package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime"
	"mime/multipart"
	"net/textproto"
	"os"
	"strings"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/google/uuid"
)

// FileInfo represents file information extracted from multipart form
type FileInfo struct {
	FieldName   string
	Filename    string
	Content     []byte
	ContentType string
}

// FileMetadata represents DynamoDB file metadata structure
type FileMetadata struct {
	FileID           string `dynamodbav:"file_id"`
	UploadTimestamp  string `dynamodbav:"upload_timestamp"`
	BucketName       string `dynamodbav:"bucket_name"`
	S3Key            string `dynamodbav:"s3_key"`
	FileName         string `dynamodbav:"file_name"`
	FileSize         int64  `dynamodbav:"file_size"`
	ContentType      string `dynamodbav:"content_type"`
	ProcessingStatus string `dynamodbav:"processing_status"`
	ETag             string `dynamodbav:"etag"`
	UploadDate       string `dynamodbav:"upload_date"`
	ExpirationTime   int64  `dynamodbav:"expiration_time"`
}

// UploadResult represents the result of a single file upload
type UploadResult struct {
	Success bool                   `json:"success"`
	Data    map[string]interface{} `json:"data,omitempty"`
	Error   string                 `json:"error,omitempty"`
}

// Response structures
type ErrorResponse struct {
	Error     string `json:"error"`
	Message   string `json:"message"`
	Timestamp string `json:"timestamp"`
}

type SuccessResponse struct {
	Success       bool                     `json:"success"`
	Message       string                   `json:"message"`
	UploadedFiles []map[string]interface{} `json:"uploadedFiles,omitempty"`
	Errors        []map[string]interface{} `json:"errors,omitempty"`
	Timestamp     string                   `json:"timestamp"`
	FileID        string                   `json:"fileId,omitempty"`
	FileName      string                   `json:"fileName,omitempty"`
	S3Key         string                   `json:"s3Key,omitempty"`
	Bucket        string                   `json:"bucket,omitempty"`
	Size          int64                    `json:"size,omitempty"`
	Status        string                   `json:"status,omitempty"`
}

var (
	s3Client      *s3.S3
	dynamoClient  *dynamodb.DynamoDB
	bucketName    string
	dynamoTable   string
)

func init() {
	sess := session.Must(session.NewSession())
	s3Client = s3.New(sess)
	dynamoClient = dynamodb.New(sess)
	
	bucketName = os.Getenv("UPLOAD_BUCKET_NAME")
	dynamoTable = os.Getenv("DYNAMODB_TABLE")
}

func main() {
	lambda.Start(handleRequest)
}

func handleRequest(ctx context.Context, request events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	// Enhanced debugging
	log.Printf("=== REQUEST DEBUG ===")
	log.Printf("Method: %s", request.HTTPMethod)
	log.Printf("Path: %s", request.Path)
	log.Printf("Body length: %d", len(request.Body))
	log.Printf("IsBase64Encoded: %v", request.IsBase64Encoded)
	
	// Log all headers with both original and lowercase keys
	log.Printf("Headers:")
	for key, value := range request.Headers {
		log.Printf("  %s: %s", key, value)
	}
	
	// Validate environment variables
	if bucketName == "" || dynamoTable == "" {
		return createErrorResponse(500, "Configuration Error", "Missing required environment variables")
	}

	// Set CORS headers
	headers := map[string]string{
		"Content-Type":                 "application/json",
		"Access-Control-Allow-Origin":  "*",
		"Access-Control-Allow-Methods": "POST, OPTIONS",
		"Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
	}

	// Handle OPTIONS request (CORS preflight)
	if request.HTTPMethod == "OPTIONS" {
		return events.APIGatewayProxyResponse{
			StatusCode: 200,
			Headers:    headers,
			Body:       "",
		}, nil
	}

	// Improved content type detection - check multiple variations
	contentType := getContentTypeFromHeaders(request.Headers)
	log.Printf("Detected Content-Type: '%s'", contentType)
	
	// Enhanced multipart detection
	isMultipartHeader := strings.Contains(strings.ToLower(contentType), "multipart/form-data")
	
	// Check if body starts with multipart boundary (even if header is missing/incorrect)
	isMultipartBody := false
	if len(request.Body) > 0 {
		// Decode body first if base64 encoded
		var bodyToCheck []byte
		if request.IsBase64Encoded {
			if decoded, err := base64.StdEncoding.DecodeString(request.Body); err == nil {
				bodyToCheck = decoded
			} else {
				bodyToCheck = []byte(request.Body)
			}
		} else {
			bodyToCheck = []byte(request.Body)
		}
		
		// Check if body starts with boundary marker
		if bytes.HasPrefix(bodyToCheck, []byte("--")) {
			isMultipartBody = true
			log.Printf("Detected multipart boundary in body")
		}
	}
	
	log.Printf("Multipart detection - Header: %v, Body: %v, Base64: %v", 
		isMultipartHeader, isMultipartBody, request.IsBase64Encoded)
	
	// Process as multipart if ANY of these conditions are true:
	// 1. Content-Type header indicates multipart
	// 2. Body starts with boundary marker
	// 3. Request is base64 encoded (likely binary data)
	if isMultipartHeader || isMultipartBody || request.IsBase64Encoded {
		log.Printf("Processing as multipart/form-data upload")
		return handleMultipartUpload(ctx, request, headers)
	} else {
		log.Printf("Processing as JSON upload")
		return handleJSONUpload(ctx, request, headers)
	}
}

// Improved header detection function
func getContentTypeFromHeaders(headers map[string]string) string {
	// Try multiple variations of content-type header
	variations := []string{
		"Content-Type",
		"content-type", 
		"Content-type",
		"CONTENT-TYPE",
	}
	
	for _, variation := range variations {
		if value, exists := headers[variation]; exists && value != "" {
			return value
		}
	}
	
	return ""
}

func handleMultipartUpload(ctx context.Context, request events.APIGatewayProxyRequest, headers map[string]string) (events.APIGatewayProxyResponse, error) {
	// Handle body decoding - API Gateway base64 encodes binary data
	var body []byte
	var err error
	
	if request.IsBase64Encoded {
		log.Printf("Decoding base64 encoded body")
		body, err = base64.StdEncoding.DecodeString(request.Body)
		if err != nil {
			log.Printf("Failed to decode base64 body: %v", err)
			return createErrorResponse(400, "Bad Request", "Invalid base64 encoding")
		}
	} else {
		log.Printf("Using raw body")
		body = []byte(request.Body)
	}
	
	log.Printf("Decoded body length: %d", len(body))

	// Parse multipart form
	contentType := getContentTypeFromHeaders(request.Headers)
	
	log.Printf("Parsing multipart with content-type: %s", contentType)
	files, err := parseMultipartFormData(body, contentType)
	if err != nil {
		log.Printf("Failed to parse multipart data: %v", err)
		return createErrorResponse(400, "Bad Request", fmt.Sprintf("Failed to parse multipart data: %v", err))
	}

	if len(files) == 0 {
		return createErrorResponse(400, "Bad Request", "No files found in upload")
	}

	// Process multiple files
	var uploadResults []map[string]interface{}
	var uploadErrors []map[string]interface{}

	for _, file := range files {
		if len(file.Content) == 0 {
			uploadErrors = append(uploadErrors, map[string]interface{}{
				"filename": file.Filename,
				"error":    "File is empty",
			})
			continue
		}

		result := processSingleFileUpload(file.Filename, file.Content, file.ContentType)
		if result.Success {
			uploadResults = append(uploadResults, result.Data)
		} else {
			uploadErrors = append(uploadErrors, map[string]interface{}{
				"filename": file.Filename,
				"error":    result.Error,
			})
		}
	}

	// Create response
	statusCode := 200
	if len(uploadResults) == 0 {
		statusCode = 400
	}

	response := SuccessResponse{
		Success:       len(uploadResults) > 0,
		Message:       fmt.Sprintf("Processed %d files: %d successful, %d failed", len(files), len(uploadResults), len(uploadErrors)),
		UploadedFiles: uploadResults,
		Errors:        uploadErrors,
		Timestamp:     time.Now().UTC().Format(time.RFC3339),
	}

	responseBody, _ := json.Marshal(response)
	return events.APIGatewayProxyResponse{
		StatusCode: statusCode,
		Headers:    headers,
		Body:       string(responseBody),
	}, nil
}

func handleJSONUpload(ctx context.Context, request events.APIGatewayProxyRequest, headers map[string]string) (events.APIGatewayProxyResponse, error) {
	return createErrorResponse(400, "Bad Request", "JSON uploads are not supported. Use multipart/form-data instead.")
}

func processSingleFileUpload(fileName string, fileBytes []byte, contentType string) UploadResult {
	// Generate unique file ID and S3 key
	fileID := uuid.New().String()
	timestamp := time.Now().UTC()
	s3Key := fmt.Sprintf("uploads/%s/%s/%s", timestamp.Format("2006/01/02"), fileID, fileName)

	log.Printf("Uploading file: %s to S3: %s", fileID, s3Key)

	// Upload file to S3
	putInput := &s3.PutObjectInput{
		Bucket:      aws.String(bucketName),
		Key:         aws.String(s3Key),
		Body:        bytes.NewReader(fileBytes),
		ContentType: aws.String(contentType),
		Metadata: map[string]*string{
			"file_id":          aws.String(fileID),
			"original_name":    aws.String(fileName),
			"upload_timestamp": aws.String(timestamp.Format(time.RFC3339)),
		},
	}

	result, err := s3Client.PutObject(putInput)
	if err != nil {
		log.Printf("Error uploading file %s: %v", fileName, err)
		return UploadResult{
			Success: false,
			Error:   fmt.Sprintf("S3 upload failed: %v", err),
		}
	}

	// Store metadata in DynamoDB
	metadata := FileMetadata{
		FileID:           fileID,
		UploadTimestamp:  timestamp.Format(time.RFC3339),
		BucketName:       bucketName,
		S3Key:            s3Key,
		FileName:         fileName,
		FileSize:         int64(len(fileBytes)),
		ContentType:      contentType,
		ProcessingStatus: "uploaded",
		ETag:             strings.Trim(*result.ETag, "\""),
		UploadDate:       timestamp.Format("2006-01-02"),
		ExpirationTime:   timestamp.Unix() + 365*24*60*60, // 1 year TTL
	}

	item, err := dynamodbattribute.MarshalMap(metadata)
	if err != nil {
		log.Printf("Error marshaling metadata for file %s: %v", fileName, err)
		return UploadResult{
			Success: false,
			Error:   fmt.Sprintf("DynamoDB marshal failed: %v", err),
		}
	}

	_, err = dynamoClient.PutItem(&dynamodb.PutItemInput{
		TableName: aws.String(dynamoTable),
		Item:      item,
	})
	if err != nil {
		log.Printf("Error storing metadata for file %s: %v", fileName, err)
		return UploadResult{
			Success: false,
			Error:   fmt.Sprintf("DynamoDB put failed: %v", err),
		}
	}

	log.Printf("Successfully uploaded file: %s to S3: %s", fileID, s3Key)

	return UploadResult{
		Success: true,
		Data: map[string]interface{}{
			"fileId":    fileID,
			"fileName":  fileName,
			"s3Key":     s3Key,
			"bucket":    bucketName,
			"size":      int64(len(fileBytes)),
			"timestamp": timestamp.Format(time.RFC3339),
			"status":    "File uploaded and queued for processing",
		},
	}
}

func parseMultipartFormData(body []byte, contentType string) ([]FileInfo, error) {
	var boundary string
	
	// Try to parse boundary from content-type header
	if contentType != "" {
		_, params, err := mime.ParseMediaType(contentType)
		if err == nil {
			boundary, _ = params["boundary"]
		}
	}
	
	// If boundary not found in header, try to extract from body
	if boundary == "" {
		// Look for boundary in first line of body
		if bytes.HasPrefix(body, []byte("--")) {
			firstLine := bytes.SplitN(body, []byte("\r\n"), 2)[0]
			boundary = strings.TrimPrefix(string(firstLine), "--")
			log.Printf("Extracted boundary from body: %s", boundary)
		} else {
			return nil, fmt.Errorf("no boundary found in content type or body")
		}
	}

	reader := multipart.NewReader(bytes.NewReader(body), boundary)
	var files []FileInfo

	for {
		part, err := reader.NextPart()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("failed to read multipart: %v", err)
		}

		// Read part content
		content, err := io.ReadAll(part)
		if err != nil {
			return nil, fmt.Errorf("failed to read part content: %v", err)
		}

		// Check if this is a file part
		if part.FileName() != "" {
			files = append(files, FileInfo{
				FieldName:   part.FormName(),
				Filename:    part.FileName(),
				Content:     content,
				ContentType: getContentType(part.Header),
			})
		}
	}

	return files, nil
}

func getContentType(header textproto.MIMEHeader) string {
	contentType := header.Get("Content-Type")
	if contentType == "" {
		return "application/octet-stream"
	}
	return contentType
}

// Updated getHeader function to be more robust
func getHeader(headers map[string]string, key string) string {
	// Try exact match first
	if val, exists := headers[key]; exists {
		return val
	}
	
	// Try lowercase
	if val, exists := headers[strings.ToLower(key)]; exists {
		return val
	}
	
	// Try title case
	if val, exists := headers[strings.Title(strings.ToLower(key))]; exists {
		return val
	}
	
	// Try uppercase
	if val, exists := headers[strings.ToUpper(key)]; exists {
		return val
	}
	
	return ""
}

func generateShortID() string {
	b := make([]byte, 4)
	rand.Read(b)
	return fmt.Sprintf("%x", b)
}

func createErrorResponse(statusCode int, errorType, message string) (events.APIGatewayProxyResponse, error) {
	headers := map[string]string{
		"Content-Type":                "application/json",
		"Access-Control-Allow-Origin": "*",
	}

	errorResponse := ErrorResponse{
		Error:     errorType,
		Message:   message,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}

	responseBody, _ := json.Marshal(errorResponse)
	return events.APIGatewayProxyResponse{
		StatusCode: statusCode,
		Headers:    headers,
		Body:       string(responseBody),
	}, nil
}