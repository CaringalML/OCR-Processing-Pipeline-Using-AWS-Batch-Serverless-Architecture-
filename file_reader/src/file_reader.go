package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
)

// FileMetadata represents DynamoDB file metadata structure
type FileMetadata struct {
	FileID           string `dynamodbav:"file_id" json:"fileId"`
	UploadTimestamp  string `dynamodbav:"upload_timestamp" json:"uploadTimestamp"`
	BucketName       string `dynamodbav:"bucket_name" json:"-"`
	S3Key            string `dynamodbav:"s3_key" json:"-"`
	FileName         string `dynamodbav:"file_name" json:"fileName"`
	FileSize         int64  `dynamodbav:"file_size" json:"fileSize"`
	ContentType      string `dynamodbav:"content_type" json:"contentType"`
	ProcessingStatus string `dynamodbav:"processing_status" json:"processingStatus"`
}

// ProcessingResult represents processing results from the results table
type ProcessingResult struct {
	FileID              string                 `dynamodbav:"file_id"`
	ExtractedText       string                 `dynamodbav:"extracted_text"`
	FormattedText       string                 `dynamodbav:"formatted_text"`
	TextFormatting      map[string]interface{} `dynamodbav:"text_formatting"`
	Analysis            map[string]interface{} `dynamodbav:"analysis"`
	ProcessingDuration  string                 `dynamodbav:"processing_duration"`
	ComprehendAnalysis  map[string]interface{} `dynamodbav:"comprehend_analysis"`
	TextractAnalysis    map[string]interface{} `dynamodbav:"textract_analysis"`
}

// Response structures
type ErrorResponse struct {
	Error   string `json:"error"`
	Message string `json:"message"`
}

type SingleFileResponse struct {
	FileID             string                 `json:"fileId"`
	FileName           string                 `json:"fileName"`
	UploadTimestamp    string                 `json:"uploadTimestamp"`
	ProcessingStatus   string                 `json:"processingStatus"`
	FileSize           int64                  `json:"fileSize"`
	ContentType        string                 `json:"contentType"`
	CloudFrontURL      string                 `json:"cloudFrontUrl"`
	ExtractedText      string                 `json:"extractedText,omitempty"`
	FormattedText      string                 `json:"formattedText,omitempty"`
	TextFormatting     map[string]interface{} `json:"textFormatting,omitempty"`
	Analysis           map[string]interface{} `json:"analysis,omitempty"`
	ProcessingDuration string                 `json:"processingDuration,omitempty"`
	ComprehendAnalysis map[string]interface{} `json:"comprehendAnalysis,omitempty"`
	TextractAnalysis   map[string]interface{} `json:"textractAnalysis,omitempty"`
}

type MultiFileResponse struct {
	Files   []SingleFileResponse `json:"files"`
	Count   int                  `json:"count"`
	HasMore bool                 `json:"hasMore"`
}

var (
	dynamoClient      *dynamodb.DynamoDB
	metadataTableName string
	resultsTableName  string
	cloudFrontDomain  string
)

func init() {
	sess := session.Must(session.NewSession())
	dynamoClient = dynamodb.New(sess)

	metadataTableName = os.Getenv("METADATA_TABLE")
	resultsTableName = os.Getenv("RESULTS_TABLE")
	cloudFrontDomain = os.Getenv("CLOUDFRONT_DOMAIN")
}

func main() {
	lambda.Start(handleRequest)
}

func handleRequest(ctx context.Context, request events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	log.Printf("Processing request: %s %s", request.HTTPMethod, request.Path)

	// Validate environment variables
	if metadataTableName == "" || resultsTableName == "" || cloudFrontDomain == "" {
		return createErrorResponse(500, "Configuration Error", "Missing required environment variables")
	}

	// Set CORS headers
	headers := map[string]string{
		"Content-Type":                "application/json",
		"Access-Control-Allow-Origin": "*",
	}

	// Handle OPTIONS request (CORS preflight)
	if request.HTTPMethod == "OPTIONS" {
		headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
		headers["Access-Control-Allow-Headers"] = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
		return events.APIGatewayProxyResponse{
			StatusCode: 200,
			Headers:    headers,
			Body:       "",
		}, nil
	}

	// Parse query parameters
	queryParams := request.QueryStringParameters
	if queryParams == nil {
		queryParams = make(map[string]string)
	}

	statusFilter := queryParams["status"]
	if statusFilter == "" {
		statusFilter = "processed"
	}

	limitStr := queryParams["limit"]
	limit := int64(50) // default
	if limitStr != "" {
		if parsedLimit, err := strconv.ParseInt(limitStr, 10, 64); err == nil {
			limit = parsedLimit
		}
	}

	fileID := queryParams["fileId"]

	// If specific file_id is requested
	if fileID != "" {
		return handleSingleFileRequest(fileID, headers)
	} else {
		return handleMultipleFilesRequest(statusFilter, limit, headers)
	}
}

func handleSingleFileRequest(fileID string, headers map[string]string) (events.APIGatewayProxyResponse, error) {
	// Get file metadata
	queryInput := &dynamodb.QueryInput{
		TableName:              aws.String(metadataTableName),
		KeyConditionExpression: aws.String("file_id = :file_id"),
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":file_id": {S: aws.String(fileID)},
		},
		Limit: aws.Int64(1),
	}

	metadataResult, err := dynamoClient.Query(queryInput)
	if err != nil {
		return createErrorResponse(500, "Database Error", fmt.Sprintf("Failed to query metadata: %v", err))
	}

	if len(metadataResult.Items) == 0 {
		return createErrorResponse(404, "Not Found", fmt.Sprintf("File %s not found", fileID))
	}

	var fileMetadata FileMetadata
	if err := dynamodbattribute.UnmarshalMap(metadataResult.Items[0], &fileMetadata); err != nil {
		return createErrorResponse(500, "Data Error", fmt.Sprintf("Failed to unmarshal metadata: %v", err))
	}

	// Get processing results
	var processingResult ProcessingResult
	getInput := &dynamodb.GetItemInput{
		TableName: aws.String(resultsTableName),
		Key: map[string]*dynamodb.AttributeValue{
			"file_id": {S: aws.String(fileID)},
		},
	}

	resultResult, err := dynamoClient.GetItem(getInput)
	if err != nil {
		log.Printf("Failed to get processing results for %s: %v", fileID, err)
		// Continue without processing results
	} else if resultResult.Item != nil {
		if err := dynamodbattribute.UnmarshalMap(resultResult.Item, &processingResult); err != nil {
			log.Printf("Failed to unmarshal processing results for %s: %v", fileID, err)
		} else {
			// Validate that essential data was retrieved
			if processingResult.ExtractedText == "" && len(processingResult.Analysis) == 0 {
				log.Printf("Warning: Processing results for %s appear to be incomplete - missing extracted text and analysis", fileID)
			}
		}
	} else {
		log.Printf("Warning: No processing results found for %s in table %s", fileID, resultsTableName)
	}

	// Generate CloudFront URL
	cloudFrontURL := fmt.Sprintf("https://%s/%s", cloudFrontDomain, fileMetadata.S3Key)

	// Build response data
	responseData := SingleFileResponse{
		FileID:           fileID,
		FileName:         fileMetadata.FileName,
		UploadTimestamp:  fileMetadata.UploadTimestamp,
		ProcessingStatus: fileMetadata.ProcessingStatus,
		FileSize:         fileMetadata.FileSize,
		ContentType:      fileMetadata.ContentType,
		CloudFrontURL:    cloudFrontURL,
	}

	// Add processing results if available - check for extracted text or analysis data
	if processingResult.ExtractedText != "" || len(processingResult.Analysis) > 0 || len(processingResult.ComprehendAnalysis) > 0 || len(processingResult.TextractAnalysis) > 0 {
		responseData.ExtractedText = processingResult.ExtractedText
		responseData.FormattedText = processingResult.FormattedText
		responseData.TextFormatting = processingResult.TextFormatting
		responseData.Analysis = processingResult.Analysis
		responseData.ProcessingDuration = processingResult.ProcessingDuration
		responseData.ComprehendAnalysis = processingResult.ComprehendAnalysis
		responseData.TextractAnalysis = processingResult.TextractAnalysis
	}

	responseBody, err := json.Marshal(responseData)
	if err != nil {
		return createErrorResponse(500, "JSON Error", fmt.Sprintf("Failed to marshal response: %v", err))
	}

	return events.APIGatewayProxyResponse{
		StatusCode: 200,
		Headers:    headers,
		Body:       string(responseBody),
	}, nil
}

func handleMultipleFilesRequest(statusFilter string, limit int64, headers map[string]string) (events.APIGatewayProxyResponse, error) {
	var queryResult *dynamodb.QueryOutput
	var scanResult *dynamodb.ScanOutput
	var err error
	var items []map[string]*dynamodb.AttributeValue

	if statusFilter == "all" {
		// Scan all files (less efficient but necessary for 'all')
		scanInput := &dynamodb.ScanInput{
			TableName: aws.String(metadataTableName),
			Limit:     aws.Int64(limit),
		}
		scanResult, err = dynamoClient.Scan(scanInput)
		if err != nil {
			return createErrorResponse(500, "Database Error", fmt.Sprintf("Failed to scan metadata: %v", err))
		}
		items = scanResult.Items
	} else {
		// Query by status using GSI
		queryInput := &dynamodb.QueryInput{
			TableName:              aws.String(metadataTableName),
			IndexName:              aws.String("StatusIndex"),
			KeyConditionExpression: aws.String("processing_status = :status"),
			ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
				":status": {S: aws.String(statusFilter)},
			},
			Limit:            aws.Int64(limit),
			ScanIndexForward: aws.Bool(false), // Most recent first
		}
		queryResult, err = dynamoClient.Query(queryInput)
		if err != nil {
			return createErrorResponse(500, "Database Error", fmt.Sprintf("Failed to query by status: %v", err))
		}
		items = queryResult.Items
	}

	// Process items and enrich with CloudFront URLs and results
	var processedItems []SingleFileResponse
	for _, item := range items {
		var fileMetadata FileMetadata
		if err := dynamodbattribute.UnmarshalMap(item, &fileMetadata); err != nil {
			log.Printf("Failed to unmarshal metadata: %v", err)
			continue
		}

		// Get processing results if status is processed
		var processingResult ProcessingResult
		if fileMetadata.ProcessingStatus == "processed" {
			getInput := &dynamodb.GetItemInput{
				TableName: aws.String(resultsTableName),
				Key: map[string]*dynamodb.AttributeValue{
					"file_id": {S: aws.String(fileMetadata.FileID)},
				},
			}

			resultResult, err := dynamoClient.GetItem(getInput)
			if err != nil {
				log.Printf("Failed to get processing results for %s: %v", fileMetadata.FileID, err)
			} else if resultResult.Item != nil {
				if err := dynamodbattribute.UnmarshalMap(resultResult.Item, &processingResult); err != nil {
					log.Printf("Failed to unmarshal processing results for %s: %v", fileMetadata.FileID, err)
				} else {
					// Validate that essential data was retrieved
					if processingResult.ExtractedText == "" && len(processingResult.Analysis) == 0 {
						log.Printf("Warning: Processing results for %s appear to be incomplete - missing extracted text and analysis", fileMetadata.FileID)
					}
				}
			} else {
				log.Printf("Warning: No processing results found for %s in table %s", fileMetadata.FileID, resultsTableName)
			}
		}

		// Generate CloudFront URL
		cloudFrontURL := fmt.Sprintf("https://%s/%s", cloudFrontDomain, fileMetadata.S3Key)

		// Build item data
		itemData := SingleFileResponse{
			FileID:           fileMetadata.FileID,
			FileName:         fileMetadata.FileName,
			UploadTimestamp:  fileMetadata.UploadTimestamp,
			ProcessingStatus: fileMetadata.ProcessingStatus,
			FileSize:         fileMetadata.FileSize,
			ContentType:      fileMetadata.ContentType,
			CloudFrontURL:    cloudFrontURL,
		}

		// Add processing results if available and status is processed - check for actual data
		if fileMetadata.ProcessingStatus == "processed" && (processingResult.ExtractedText != "" || len(processingResult.Analysis) > 0 || len(processingResult.ComprehendAnalysis) > 0 || len(processingResult.TextractAnalysis) > 0) {
			itemData.ExtractedText = processingResult.ExtractedText
			itemData.FormattedText = processingResult.FormattedText
			itemData.TextFormatting = processingResult.TextFormatting
			itemData.Analysis = processingResult.Analysis
			itemData.ProcessingDuration = processingResult.ProcessingDuration
			itemData.ComprehendAnalysis = processingResult.ComprehendAnalysis
			itemData.TextractAnalysis = processingResult.TextractAnalysis
		}

		processedItems = append(processedItems, itemData)
	}

	// Determine if there are more items
	hasMore := false
	if statusFilter == "all" && scanResult != nil {
		hasMore = scanResult.LastEvaluatedKey != nil
	} else if queryResult != nil {
		hasMore = queryResult.LastEvaluatedKey != nil
	}

	responseData := MultiFileResponse{
		Files:   processedItems,
		Count:   len(processedItems),
		HasMore: hasMore,
	}

	responseBody, err := json.Marshal(responseData)
	if err != nil {
		return createErrorResponse(500, "JSON Error", fmt.Sprintf("Failed to marshal response: %v", err))
	}

	return events.APIGatewayProxyResponse{
		StatusCode: 200,
		Headers:    headers,
		Body:       string(responseBody),
	}, nil
}

func createErrorResponse(statusCode int, errorType, message string) (events.APIGatewayProxyResponse, error) {
	headers := map[string]string{
		"Content-Type":                "application/json",
		"Access-Control-Allow-Origin": "*",
	}

	errorResponse := ErrorResponse{
		Error:   errorType,
		Message: message,
	}

	responseBody, _ := json.Marshal(errorResponse)
	return events.APIGatewayProxyResponse{
		StatusCode: statusCode,
		Headers:    headers,
		Body:       string(responseBody),
	}, nil
}