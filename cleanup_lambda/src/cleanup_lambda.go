package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/batch"
	"github.com/aws/aws-sdk-go/service/ecs"
)

// CleanupResults represents the results of the cleanup operation
type CleanupResults struct {
	OCRBatchJobsCleaned int      `json:"ocr_batch_jobs_cleaned"`
	ECSTasksCleaned     int      `json:"ecs_tasks_cleaned"`
	Errors              []string `json:"errors"`
}

// Response represents the Lambda response structure
type Response struct {
	StatusCode int                    `json:"statusCode"`
	Body       map[string]interface{} `json:"body"`
}

var (
	batchClient *batch.Batch
	ecsClient   *ecs.ECS
	jobQueue    string
	cleanupAge  int
)

func init() {
	sess := session.Must(session.NewSession())
	batchClient = batch.New(sess)
	ecsClient = ecs.New(sess)

	jobQueue = os.Getenv("BATCH_JOB_QUEUE")
	
	cleanupAgeStr := os.Getenv("CLEANUP_AGE_HOURS")
	if cleanupAgeStr == "" {
		cleanupAge = 24 // default 24 hours
	} else {
		var err error
		cleanupAge, err = strconv.Atoi(cleanupAgeStr)
		if err != nil {
			log.Printf("Invalid CLEANUP_AGE_HOURS value: %s, using default 24", cleanupAgeStr)
			cleanupAge = 24
		}
	}
}

func main() {
	lambda.Start(handleRequest)
}

func handleRequest(ctx context.Context, event interface{}) (Response, error) {
	log.Printf("Starting automated cleanup process for OCR processing infrastructure...")

	results := CleanupResults{
		OCRBatchJobsCleaned: 0,
		ECSTasksCleaned:     0,
		Errors:              []string{},
	}

	log.Printf("OCR Cleanup Configuration - Job Queue: %s, Cleanup Age: %d hours", jobQueue, cleanupAge)

	// Validate environment variables
	if jobQueue == "" {
		errMsg := "Missing required environment variable: BATCH_JOB_QUEUE"
		log.Printf("ERROR: %s", errMsg)
		results.Errors = append(results.Errors, errMsg)
		return createErrorResponse(results, errMsg), nil
	}

	// Clean up AWS Batch OCR processing jobs
	batchCleaned, err := cleanupOCRBatchJobs()
	if err != nil {
		errMsg := fmt.Sprintf("Failed to cleanup batch jobs: %v", err)
		log.Printf("ERROR: %s", errMsg)
		results.Errors = append(results.Errors, errMsg)
	} else {
		results.OCRBatchJobsCleaned = batchCleaned
	}

	// Clean up ECS tasks
	ecsCleaned, err := cleanupECSTasks()
	if err != nil {
		errMsg := fmt.Sprintf("Failed to cleanup ECS tasks: %v", err)
		log.Printf("ERROR: %s", errMsg)
		results.Errors = append(results.Errors, errMsg)
	} else {
		results.ECSTasksCleaned = ecsCleaned
	}

	log.Printf("OCR cleanup completed: %+v", results)

	if len(results.Errors) > 0 {
		return createErrorResponse(results, "OCR processing cleanup completed with errors"), nil
	}

	return Response{
		StatusCode: 200,
		Body: map[string]interface{}{
			"message":   "OCR processing cleanup completed successfully",
			"results":   results,
			"timestamp": time.Now().UTC().Format(time.RFC3339),
		},
	}, nil
}

func cleanupOCRBatchJobs() (int, error) {
	log.Printf("Cleaning up OCR Batch jobs older than %d hours...", cleanupAge)

	cleanupCount := 0
	cutoffTime := time.Now().UTC().Add(-time.Duration(cleanupAge) * time.Hour)

	// Get OCR processing jobs in different states
	jobStates := []string{"SUCCEEDED", "FAILED", "RUNNABLE", "PENDING", "RUNNING"}

	for _, state := range jobStates {
		input := &batch.ListJobsInput{
			JobQueue:   aws.String(jobQueue),
			JobStatus:  aws.String(state),
			MaxResults: aws.Int64(100),
		}

		result, err := batchClient.ListJobs(input)
		if err != nil {
			log.Printf("Error listing %s OCR jobs: %v", state, err)
			continue
		}

		for _, job := range result.JobSummaryList {
			jobName := aws.StringValue(job.JobName)
			
			// Only process OCR processor jobs (check for pattern that matches the job naming)
			if !strings.Contains(jobName, "process-file-") {
				continue
			}

			// Check job age
			var jobTime time.Time
			if job.StoppedAt != nil {
				jobTime = time.Unix(*job.StoppedAt/1000, 0)
			} else if job.CreatedAt != nil {
				jobTime = time.Unix(*job.CreatedAt/1000, 0)
			} else {
				continue
			}

			if jobTime.Before(cutoffTime) {
				jobID := aws.StringValue(job.JobId)
				log.Printf("Found old OCR Batch job for cleanup: %s (state: %s)", jobID, state)

				// For running jobs, cancel them; for completed jobs, just log
				if state == "RUNNABLE" || state == "PENDING" || state == "RUNNING" {
					cancelInput := &batch.CancelJobInput{
						JobId:  aws.String(jobID),
						Reason: aws.String(fmt.Sprintf("Automated OCR cleanup - job older than %d hours", cleanupAge)),
					}

					_, err := batchClient.CancelJob(cancelInput)
					if err != nil {
						log.Printf("Failed to cancel OCR job %s: %v", jobID, err)
						continue
					}
					log.Printf("Cancelled running OCR job: %s", jobID)
				}
				cleanupCount++
			}
		}
	}

	log.Printf("Processed %d OCR Batch jobs", cleanupCount)
	return cleanupCount, nil
}

func cleanupECSTasks() (int, error) {
	log.Printf("Cleaning up ECS OCR processing tasks older than %d hours...", cleanupAge)

	cleanupCount := 0
	cutoffTime := time.Now().UTC().Add(-time.Duration(cleanupAge) * time.Hour)

	// List all clusters
	clustersInput := &ecs.ListClustersInput{}
	clustersResult, err := ecsClient.ListClusters(clustersInput)
	if err != nil {
		return 0, fmt.Errorf("error listing ECS clusters: %v", err)
	}

	for _, clusterArn := range clustersResult.ClusterArns {
		// List stopped tasks in cluster
		tasksInput := &ecs.ListTasksInput{
			Cluster:       clusterArn,
			DesiredStatus: aws.String("STOPPED"),
			MaxResults:    aws.Int64(100),
		}

		tasksResult, err := ecsClient.ListTasks(tasksInput)
		if err != nil {
			log.Printf("Error listing tasks in cluster %s: %v", aws.StringValue(clusterArn), err)
			continue
		}

		if len(tasksResult.TaskArns) == 0 {
			continue
		}

		// Describe tasks to get details
		describeInput := &ecs.DescribeTasksInput{
			Cluster: clusterArn,
			Tasks:   tasksResult.TaskArns,
		}

		taskDetails, err := ecsClient.DescribeTasks(describeInput)
		if err != nil {
			log.Printf("Error describing tasks in cluster %s: %v", aws.StringValue(clusterArn), err)
			continue
		}

		for _, task := range taskDetails.Tasks {
			// Only process OCR processor related tasks
			taskDefinition := aws.StringValue(task.TaskDefinitionArn)
			if !strings.Contains(taskDefinition, "ocr-processor") {
				continue
			}

			// Check task age
			var taskTime time.Time
			if task.StoppedAt != nil {
				taskTime = *task.StoppedAt
			} else if task.CreatedAt != nil {
				taskTime = *task.CreatedAt
			} else {
				continue
			}

			if taskTime.Before(cutoffTime) {
				taskArn := aws.StringValue(task.TaskArn)
				log.Printf("Found old OCR ECS task: %s", taskArn)
				cleanupCount++
			}
		}
	}

	log.Printf("Processed %d OCR ECS tasks", cleanupCount)
	return cleanupCount, nil
}

func createErrorResponse(results CleanupResults, message string) Response {
	return Response{
		StatusCode: 500,
		Body: map[string]interface{}{
			"message":   message,
			"error":     strings.Join(results.Errors, "; "),
			"results":   results,
			"timestamp": time.Now().UTC().Format(time.RFC3339),
		},
	}
}