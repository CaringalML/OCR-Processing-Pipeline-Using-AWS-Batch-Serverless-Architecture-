package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/batch"
	"github.com/aws/aws-sdk-go/service/dynamodb"
)

// EventBridge Batch job state change event structure
type BatchJobDetail struct {
	JobID        string `json:"jobId"`
	JobName      string `json:"jobName"`
	JobStatus    string `json:"jobStatus"`
	StatusReason string `json:"statusReason"`
}

type EventBridgeEvent struct {
	Detail BatchJobDetail `json:"detail"`
}

// Response structure
type Response struct {
	StatusCode int    `json:"statusCode"`
	Body       string `json:"body"`
}

var (
	batchClient  *batch.Batch
	dynamoClient *dynamodb.DynamoDB
	dynamoTable  string
)

func init() {
	sess := session.Must(session.NewSession())
	batchClient = batch.New(sess)
	dynamoClient = dynamodb.New(sess)

	dynamoTable = os.Getenv("DYNAMODB_TABLE")
}

func main() {
	lambda.Start(handleRequest)
}

func handleRequest(ctx context.Context, event EventBridgeEvent) (Response, error) {
	log.Printf("Received event: %+v", event)

	// Validate environment variables
	if dynamoTable == "" {
		log.Printf("ERROR: DYNAMODB_TABLE environment variable not set")
		return Response{
			StatusCode: 500,
			Body:       "DynamoDB table name not configured",
		}, nil
	}

	// Extract job details from EventBridge event
	detail := event.Detail
	jobID := detail.JobID
	jobName := detail.JobName
	jobStatus := detail.JobStatus

	if jobID == "" || jobName == "" || jobStatus == "" {
		log.Printf("ERROR: Missing required job details in event: %+v", detail)
		return Response{
			StatusCode: 400,
			Body:       "Missing required job details",
		}, nil
	}

	log.Printf("Processing job status change: %s -> %s", jobName, jobStatus)

	// Extract file_id from job name (format: process-file-{file_id}-{timestamp})
	fileID := extractFileIDFromJobName(jobName)
	if fileID == "" {
		log.Printf("ERROR: Could not extract file_id from job name: %s", jobName)
		return Response{
			StatusCode: 400,
			Body:       "Could not extract file_id from job name",
		}, nil
	}

	// Update DynamoDB record based on job status
	var err error
	switch jobStatus {
	case "SUCCEEDED":
		err = updateStatusToProcessed(fileID, jobID)
	case "FAILED":
		err = updateStatusToFailed(fileID, jobID, detail)
	default:
		log.Printf("WARNING: Unexpected job status: %s", jobStatus)
		return Response{
			StatusCode: 200,
			Body:       fmt.Sprintf("No action taken for status: %s", jobStatus),
		}, nil
	}

	if err != nil {
		log.Printf("ERROR: Failed to update status for file_id %s: %v", fileID, err)
		return Response{
			StatusCode: 500,
			Body:       fmt.Sprintf("Error: %v", err),
		}, nil
	}

	log.Printf("Successfully updated status for file_id: %s", fileID)
	return Response{
		StatusCode: 200,
		Body:       fmt.Sprintf("Successfully processed job %s", jobID),
	}, nil
}

func extractFileIDFromJobName(jobName string) string {
	// Job name format: process-file-{file_id}-{timestamp}
	parts := strings.Split(jobName, "-")
	if len(parts) >= 4 && parts[0] == "process" && parts[1] == "file" {
		// Join all parts except the first two (process-file) and the last one (timestamp)
		fileID := strings.Join(parts[2:len(parts)-1], "-")
		return fileID
	}
	return ""
}

func updateStatusToProcessed(fileID, jobID string) error {
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
		ConditionExpression: aws.String("attribute_exists(file_id) AND processing_status = :processing_status"),
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":status":              {S: aws.String("processed")},
			":completed":           {N: aws.String(fmt.Sprintf("%d", currentTime))},
			":updated":             {N: aws.String(fmt.Sprintf("%d", currentTime))},
			":batch_status":        {S: aws.String("SUCCEEDED")},
			":processing_status":   {S: aws.String("processing")},
		},
		ReturnValues: aws.String("UPDATED_NEW"),
	}

	_, err = dynamoClient.UpdateItem(updateInput)
	if err != nil {
		// Check for conditional check failed exception
		if strings.Contains(err.Error(), "ConditionalCheckFailedException") {
			log.Printf("WARNING: File %s not in processing status or doesn't exist - skipping update", fileID)
			return nil
		}
		return fmt.Errorf("failed to update file %s to processed: %v", fileID, err)
	}

	log.Printf("Updated file_id %s to processed status", fileID)
	return nil
}

func updateStatusToFailed(fileID, jobID string, jobDetail BatchJobDetail) error {
	currentTime := time.Now().Unix()

	// First, get the upload_timestamp for the composite key
	uploadTimestamp, err := getUploadTimestamp(fileID)
	if err != nil {
		return fmt.Errorf("failed to get upload timestamp: %v", err)
	}

	// Extract failure reason from job detail
	statusReason := jobDetail.StatusReason
	if statusReason == "" {
		statusReason = "Batch job failed"
	}

	updateInput := &dynamodb.UpdateItemInput{
		TableName: aws.String(dynamoTable),
		Key: map[string]*dynamodb.AttributeValue{
			"file_id":          {S: aws.String(fileID)},
			"upload_timestamp": {S: aws.String(uploadTimestamp)},
		},
		UpdateExpression: aws.String("SET processing_status = :status, failed_at = :failed_at, last_updated = :updated, error_message = :error, batch_job_final_status = :batch_status"),
		ConditionExpression: aws.String("attribute_exists(file_id) AND processing_status = :processing_status"),
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":status":              {S: aws.String("failed")},
			":failed_at":           {N: aws.String(fmt.Sprintf("%d", currentTime))},
			":updated":             {N: aws.String(fmt.Sprintf("%d", currentTime))},
			":error":               {S: aws.String(fmt.Sprintf("Batch job failed: %s", statusReason))},
			":batch_status":        {S: aws.String("FAILED")},
			":processing_status":   {S: aws.String("processing")},
		},
		ReturnValues: aws.String("UPDATED_NEW"),
	}

	_, err = dynamoClient.UpdateItem(updateInput)
	if err != nil {
		// Check for conditional check failed exception
		if strings.Contains(err.Error(), "ConditionalCheckFailedException") {
			log.Printf("WARNING: File %s not in processing status or doesn't exist - skipping update", fileID)
			return nil
		}
		return fmt.Errorf("failed to update file %s to failed: %v", fileID, err)
	}

	log.Printf("Updated file_id %s to failed status", fileID)
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