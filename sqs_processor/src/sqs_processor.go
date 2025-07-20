package main

import (
	"context"
	"encoding/json"
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
	"github.com/aws/aws-sdk-go/service/sqs"
)

// EventBridge S3 event structure
type S3EventDetail struct {
	Bucket struct {
		Name string `json:"name"`
	} `json:"bucket"`
	Object struct {
		Key string `json:"key"`
	} `json:"object"`
}

type EventBridgeEvent struct {
	Detail S3EventDetail `json:"detail"`
}

// Response structure
type ProcessingResponse struct {
	StatusCode int                    `json:"statusCode"`
	Body       map[string]interface{} `json:"body"`
}

var (
	sqsClient     *sqs.SQS
	batchClient   *batch.Batch
	dynamoClient  *dynamodb.DynamoDB
	queueURL      string
	jobQueue      string
	jobDefinition string
	dynamoTable   string
)

func init() {
	sess := session.Must(session.NewSession())
	sqsClient = sqs.New(sess)
	batchClient = batch.New(sess)
	dynamoClient = dynamodb.New(sess)

	queueURL = os.Getenv("SQS_QUEUE_URL")
	jobQueue = os.Getenv("BATCH_JOB_QUEUE")
	jobDefinition = os.Getenv("BATCH_JOB_DEFINITION")
	dynamoTable = os.Getenv("DYNAMODB_TABLE")
}

func main() {
	lambda.Start(handleRequest)
}

func handleRequest(ctx context.Context, event interface{}) (ProcessingResponse, error) {
	log.Printf("Processing SQS messages for S3 file processing")

	// Validate environment variables
	if queueURL == "" || jobQueue == "" || jobDefinition == "" || dynamoTable == "" {
		log.Printf("ERROR: Missing required environment variables")
		return ProcessingResponse{
			StatusCode: 500,
			Body: map[string]interface{}{
				"error": "Configuration error",
			},
		}, nil
	}

	processedCount := 0
	errorCount := 0

	// Receive messages from SQS
	receiveInput := &sqs.ReceiveMessageInput{
		QueueUrl:              aws.String(queueURL),
		MaxNumberOfMessages:   aws.Int64(10),
		WaitTimeSeconds:       aws.Int64(5),
		MessageAttributeNames: []*string{aws.String("All")},
	}

	result, err := sqsClient.ReceiveMessage(receiveInput)
	if err != nil {
		log.Printf("ERROR: Failed to receive messages: %v", err)
		return ProcessingResponse{
			StatusCode: 500,
			Body: map[string]interface{}{
				"error": err.Error(),
			},
		}, nil
	}

	messages := result.Messages

	for _, message := range messages {
		if err := processMessage(message); err != nil {
			log.Printf("Error processing message: %v", err)
			errorCount++
		} else {
			processedCount++
		}
	}

	log.Printf("Processed %d messages, %d errors", processedCount, errorCount)

	return ProcessingResponse{
		StatusCode: 200,
		Body: map[string]interface{}{
			"processed":      processedCount,
			"errors":         errorCount,
			"total_messages": len(messages),
		},
	}, nil
}

func processMessage(message *sqs.Message) error {
	// Parse the message body
	var eventBody EventBridgeEvent
	if err := json.Unmarshal([]byte(*message.Body), &eventBody); err != nil {
		log.Printf("Invalid message format: %v", err)
		return err
	}

	detail := eventBody.Detail
	bucketName := detail.Bucket.Name
	objectKey := detail.Object.Key

	// Skip if not in uploads folder
	if !strings.HasPrefix(objectKey, "uploads/") {
		log.Printf("Skipping non-upload file: %s", objectKey)
		return deleteMessage(*message.ReceiptHandle)
	}

	// Extract file_id from the key structure
	// Format: uploads/YYYY/MM/DD/{file_id}/{filename}
	keyParts := strings.Split(objectKey, "/")
	if len(keyParts) < 6 {
		log.Printf("Invalid key structure: %s", objectKey)
		return deleteMessage(*message.ReceiptHandle)
	}

	fileID := keyParts[4]

	// Submit Batch job
	jobName := fmt.Sprintf("process-file-%s-%s", fileID, time.Now().Format("20060102150405"))

	submitInput := &batch.SubmitJobInput{
		JobName:       aws.String(jobName),
		JobQueue:      aws.String(jobQueue),
		JobDefinition: aws.String(jobDefinition),
		Parameters: map[string]*string{
			"bucket": aws.String(bucketName),
			"key":    aws.String(objectKey),
			"fileId": aws.String(fileID),
		},
		ContainerOverrides: &batch.ContainerOverrides{
			Environment: []*batch.KeyValuePair{
				{Name: aws.String("S3_BUCKET"), Value: aws.String(bucketName)},
				{Name: aws.String("S3_KEY"), Value: aws.String(objectKey)},
				{Name: aws.String("FILE_ID"), Value: aws.String(fileID)},
				{Name: aws.String("DYNAMODB_TABLE"), Value: aws.String(dynamoTable)},
			},
		},
	}

	batchResult, err := batchClient.SubmitJob(submitInput)
	if err != nil {
		log.Printf("Failed to submit batch job for file %s: %v", fileID, err)
		return err
	}

	jobID := *batchResult.JobId
	log.Printf("Submitted Batch job %s for file %s", jobID, fileID)

	// Update DynamoDB with job information
	if err := updateFileMetadata(fileID, jobID, jobName); err != nil {
		log.Printf("Failed to update metadata for file %s: %v", fileID, err)
		return err
	}

	// Delete message from queue after successful processing
	return deleteMessage(*message.ReceiptHandle)
}

func updateFileMetadata(fileID, jobID, jobName string) error {
	// First, query to get the correct upload_timestamp
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
		return fmt.Errorf("failed to query file metadata: %v", err)
	}

	if len(result.Items) == 0 {
		return fmt.Errorf("file metadata not found for file_id: %s", fileID)
	}

	// Get the upload timestamp directly from the result
	uploadTimestamp := *result.Items[0]["upload_timestamp"].S

	// Update the item with job information
	updateInput := &dynamodb.UpdateItemInput{
		TableName: aws.String(dynamoTable),
		Key: map[string]*dynamodb.AttributeValue{
			"file_id":          {S: aws.String(fileID)},
			"upload_timestamp": {S: aws.String(uploadTimestamp)},
		},
		UpdateExpression: aws.String("SET processing_status = :status, batch_job_id = :job_id, batch_job_name = :job_name, last_updated = :updated"),
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":status":   {S: aws.String("processing")},
			":job_id":   {S: aws.String(jobID)},
			":job_name": {S: aws.String(jobName)},
			":updated":  {S: aws.String(time.Now().UTC().Format(time.RFC3339))},
		},
	}

	_, err = dynamoClient.UpdateItem(updateInput)
	if err != nil {
		return fmt.Errorf("failed to update file metadata: %v", err)
	}

	return nil
}

func deleteMessage(receiptHandle string) error {
	deleteInput := &sqs.DeleteMessageInput{
		QueueUrl:      aws.String(queueURL),
		ReceiptHandle: aws.String(receiptHandle),
	}

	_, err := sqsClient.DeleteMessage(deleteInput)
	if err != nil {
		log.Printf("Error deleting message: %v", err)
		return err
	}

	return nil
}