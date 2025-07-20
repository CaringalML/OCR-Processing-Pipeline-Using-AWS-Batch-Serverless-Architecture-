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
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
)

// StuckJob represents a job stuck in processing status
type StuckJob struct {
	FileID            string `dynamodbav:"file_id"`
	UploadTimestamp   string `dynamodbav:"upload_timestamp"`
	BatchJobID        string `dynamodbav:"batch_job_id"`
	ProcessingStarted int64  `dynamodbav:"processing_started"`
}

// ProcessingResult represents the result of processing a stuck job
type ProcessingResult struct {
	FileID  string `json:"file_id"`
	Action  string `json:"action"`
	Reason  string `json:"reason"`
	Success bool   `json:"success"`
}

// Response structure
type Response struct {
	StatusCode int                    `json:"statusCode"`
	Body       map[string]interface{} `json:"body"`
}

var (
	batchClient         *batch.Batch
	dynamoClient        *dynamodb.DynamoDB
	dynamoTable         string
	maxProcessingMinutes int64
)

func init() {
	sess := session.Must(session.NewSession())
	batchClient = batch.New(sess)
	dynamoClient = dynamodb.New(sess)

	dynamoTable = os.Getenv("DYNAMODB_TABLE")
	maxProcessingMinutesStr := os.Getenv("MAX_PROCESSING_MINUTES")
	if maxProcessingMinutesStr == "" {
		maxProcessingMinutes = 120 // Default 2 hours
	} else {
		var err error
		maxProcessingMinutes, err = strconv.ParseInt(maxProcessingMinutesStr, 10, 64)
		if err != nil {
			maxProcessingMinutes = 120
		}
	}
}

func main() {
	lambda.Start(handleRequest)
}

func handleRequest(ctx context.Context, event interface{}) (Response, error) {
	log.Printf("Starting dead job detection")

	// Validate environment variables
	if dynamoTable == "" {
		log.Printf("ERROR: DYNAMODB_TABLE environment variable not set")
		return Response{
			StatusCode: 500,
			Body: map[string]interface{}{
				"error": "DynamoDB table name not configured",
			},
		}, nil
	}

	// Find jobs stuck in processing status
	stuckJobs, err := findStuckProcessingJobs()
	if err != nil {
		log.Printf("ERROR: Failed to find stuck jobs: %v", err)
		return Response{
			StatusCode: 500,
			Body: map[string]interface{}{
				"error": err.Error(),
			},
		}, nil
	}

	if len(stuckJobs) == 0 {
		log.Printf("No stuck jobs found")
		return Response{
			StatusCode: 200,
			Body: map[string]interface{}{
				"message": "No stuck jobs found",
			},
		}, nil
	}

	log.Printf("Found %d stuck jobs", len(stuckJobs))

	// Process each stuck job
	var results []ProcessingResult
	for _, job := range stuckJobs {
		result := processStuckJob(job)
		results = append(results, result)
	}

	successCount := 0
	for _, r := range results {
		if r.Success {
			successCount++
		}
	}

	log.Printf("Processed %d stuck jobs, %d successful", len(stuckJobs), successCount)

	return Response{
		StatusCode: 200,
		Body: map[string]interface{}{
			"message":    fmt.Sprintf("Processed %d stuck jobs", len(stuckJobs)),
			"successful": successCount,
			"failed":     len(stuckJobs) - successCount,
			"results":    results,
		},
	}, nil
}

func findStuckProcessingJobs() ([]StuckJob, error) {
	// Calculate cutoff time
	cutoffTime := time.Now().Unix() - (maxProcessingMinutes * 60)

	scanInput := &dynamodb.ScanInput{
		TableName:        aws.String(dynamoTable),
		FilterExpression: aws.String("processing_status = :status AND processing_started < :cutoff"),
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":status": {S: aws.String("processing")},
			":cutoff": {N: aws.String(fmt.Sprintf("%d", cutoffTime))},
		},
	}

	result, err := dynamoClient.Scan(scanInput)
	if err != nil {
		return nil, fmt.Errorf("failed to scan for stuck jobs: %v", err)
	}

	var stuckJobs []StuckJob
	for _, item := range result.Items {
		var job StuckJob
		if err := dynamodbattribute.UnmarshalMap(item, &job); err != nil {
			log.Printf("Failed to unmarshal stuck job: %v", err)
			continue
		}
		stuckJobs = append(stuckJobs, job)
	}

	log.Printf("Found %d jobs stuck in processing status", len(stuckJobs))
	return stuckJobs, nil
}

func processStuckJob(job StuckJob) ProcessingResult {
	fileID := job.FileID
	batchJobID := job.BatchJobID

	log.Printf("Processing stuck job: file_id=%s, batch_job_id=%s", fileID, batchJobID)

	// If no batch job ID, mark as failed
	if batchJobID == "" {
		log.Printf("WARNING: No batch_job_id for file_id %s, marking as failed", fileID)
		if err := updateStatusToFailed(fileID, "No batch job ID found"); err != nil {
			return ProcessingResult{
				FileID:  fileID,
				Action:  "error",
				Reason:  err.Error(),
				Success: false,
			}
		}
		return ProcessingResult{
			FileID:  fileID,
			Action:  "marked_failed",
			Reason:  "no_batch_job_id",
			Success: true,
		}
	}

	// Check actual Batch job status
	describeInput := &batch.DescribeJobsInput{
		Jobs: []*string{aws.String(batchJobID)},
	}

	batchResult, err := batchClient.DescribeJobs(describeInput)
	if err != nil {
		log.Printf("ERROR: Error checking batch job %s: %v", batchJobID, err)
		// If we can't check the batch job, mark as failed
		if err := updateStatusToFailed(fileID, fmt.Sprintf("Error checking batch job: %v", err)); err != nil {
			return ProcessingResult{
				FileID:  fileID,
				Action:  "error",
				Reason:  err.Error(),
				Success: false,
			}
		}
		return ProcessingResult{
			FileID:  fileID,
			Action:  "marked_failed",
			Reason:  "batch_check_error",
			Success: true,
		}
	}

	jobs := batchResult.Jobs
	if len(jobs) == 0 {
		log.Printf("WARNING: Batch job %s not found, marking as failed", batchJobID)
		if err := updateStatusToFailed(fileID, fmt.Sprintf("Batch job %s not found", batchJobID)); err != nil {
			return ProcessingResult{
				FileID:  fileID,
				Action:  "error",
				Reason:  err.Error(),
				Success: false,
			}
		}
		return ProcessingResult{
			FileID:  fileID,
			Action:  "marked_failed",
			Reason:  "batch_job_not_found",
			Success: true,
		}
	}

	batchJob := jobs[0]
	batchStatus := *batchJob.Status

	log.Printf("Batch job %s status: %s", batchJobID, batchStatus)

	// Handle based on actual Batch status
	switch batchStatus {
	case "SUCCEEDED":
		if err := updateStatusToProcessed(fileID, batchJobID); err != nil {
			return ProcessingResult{
				FileID:  fileID,
				Action:  "error",
				Reason:  err.Error(),
				Success: false,
			}
		}
		return ProcessingResult{
			FileID:  fileID,
			Action:  "marked_processed",
			Reason:  "batch_job_succeeded",
			Success: true,
		}
	case "FAILED", "CANCELLED":
		statusReason := "Batch job " + strings.ToLower(batchStatus)
		if batchJob.StatusReason != nil {
			statusReason = fmt.Sprintf("Batch job %s: %s", strings.ToLower(batchStatus), *batchJob.StatusReason)
		}
		if err := updateStatusToFailed(fileID, statusReason); err != nil {
			return ProcessingResult{
				FileID:  fileID,
				Action:  "error",
				Reason:  err.Error(),
				Success: false,
			}
		}
		return ProcessingResult{
			FileID:  fileID,
			Action:  "marked_failed",
			Reason:  fmt.Sprintf("batch_job_%s", strings.ToLower(batchStatus)),
			Success: true,
		}
	case "SUBMITTED", "PENDING", "RUNNABLE", "STARTING", "RUNNING":
		// Job is still active in Batch, leave it alone for now
		log.Printf("Batch job %s is still active (%s), leaving unchanged", batchJobID, batchStatus)
		return ProcessingResult{
			FileID:  fileID,
			Action:  "no_change",
			Reason:  fmt.Sprintf("batch_job_still_%s", strings.ToLower(batchStatus)),
			Success: true,
		}
	default:
		log.Printf("WARNING: Unknown batch status %s for job %s", batchStatus, batchJobID)
		return ProcessingResult{
			FileID:  fileID,
			Action:  "no_change",
			Reason:  fmt.Sprintf("unknown_batch_status_%s", batchStatus),
			Success: true,
		}
	}
}

func updateStatusToProcessed(fileID, batchJobID string) error {
	currentTime := time.Now().Unix()

	// First, get the upload_timestamp for the composite key
	uploadTimestamp, err := getUploadTimestamp(fileID)
	if err != nil {
		return fmt.Errorf("failed to get upload timestamp: %v", err)
	}

	updateInput := &dynamodb.UpdateItemInput{
		TableName: aws.String(dynamoTable),
		Key: map[string]*dynamodb.AttributeValue{
			"file_id":          {S: aws.String(fileID)},
			"upload_timestamp": {S: aws.String(uploadTimestamp)},
		},
		UpdateExpression: aws.String("SET processing_status = :status, processing_completed = :completed, last_updated = :updated, batch_job_final_status = :batch_status"),
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":status":       {S: aws.String("processed")},
			":completed":    {N: aws.String(fmt.Sprintf("%d", currentTime))},
			":updated":      {N: aws.String(fmt.Sprintf("%d", currentTime))},
			":batch_status": {S: aws.String("SUCCEEDED")},
		},
		ConditionExpression: aws.String("attribute_exists(file_id)"),
	}

	_, err = dynamoClient.UpdateItem(updateInput)
	if err != nil {
		return fmt.Errorf("failed to update file %s to processed: %v", fileID, err)
	}

	log.Printf("Updated file_id %s to processed status", fileID)
	return nil
}

func updateStatusToFailed(fileID, errorMessage string) error {
	currentTime := time.Now().Unix()

	// First, get the upload_timestamp for the composite key
	uploadTimestamp, err := getUploadTimestamp(fileID)
	if err != nil {
		return fmt.Errorf("failed to get upload timestamp: %v", err)
	}

	updateInput := &dynamodb.UpdateItemInput{
		TableName: aws.String(dynamoTable),
		Key: map[string]*dynamodb.AttributeValue{
			"file_id":          {S: aws.String(fileID)},
			"upload_timestamp": {S: aws.String(uploadTimestamp)},
		},
		UpdateExpression: aws.String("SET processing_status = :status, failed_at = :failed_at, last_updated = :updated, error_message = :error, batch_job_final_status = :batch_status"),
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":status":       {S: aws.String("failed")},
			":failed_at":    {N: aws.String(fmt.Sprintf("%d", currentTime))},
			":updated":      {N: aws.String(fmt.Sprintf("%d", currentTime))},
			":error":        {S: aws.String(fmt.Sprintf("Dead job detection: %s", errorMessage))},
			":batch_status": {S: aws.String("FAILED")},
		},
		ConditionExpression: aws.String("attribute_exists(file_id)"),
	}

	_, err = dynamoClient.UpdateItem(updateInput)
	if err != nil {
		return fmt.Errorf("failed to update file %s to failed: %v", fileID, err)
	}

	log.Printf("Updated file_id %s to failed status: %s", fileID, errorMessage)
	return nil
}

func getUploadTimestamp(fileID string) (string, error) {
	queryInput := &dynamodb.QueryInput{
		TableName:              aws.String(dynamoTable),
		KeyConditionExpression: aws.String("file_id = :file_id"),
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":file_id": {S: aws.String(fileID)},
		},
		Limit: aws.Int64(1),
	}

	result, err := dynamoClient.Query(queryInput)
	if err != nil {
		return "", fmt.Errorf("failed to query file metadata: %v", err)
	}

	if len(result.Items) == 0 {
		return "", fmt.Errorf("file metadata not found for file_id: %s", fileID)
	}

	uploadTimestamp := result.Items[0]["upload_timestamp"]
	if uploadTimestamp.S == nil {
		return "", fmt.Errorf("upload_timestamp not found for file_id: %s", fileID)
	}

	return *uploadTimestamp.S, nil
}