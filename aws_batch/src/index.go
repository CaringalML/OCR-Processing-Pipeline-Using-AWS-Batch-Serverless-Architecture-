package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"regexp"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/comprehend"
	comprehendTypes "github.com/aws/aws-sdk-go-v2/service/comprehend/types"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	dynamodbTypes "github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/textract"
	textractTypes "github.com/aws/aws-sdk-go-v2/service/textract/types"
)

// Logger configuration
type LogLevel int

const (
	ERROR LogLevel = iota
	WARN
	INFO
	DEBUG
)

type Logger struct {
	level LogLevel
	mu    sync.Mutex
}

type LogEntry struct {
	Timestamp  string                 `json:"timestamp"`
	Level      string                 `json:"level"`
	Message    string                 `json:"message"`
	BatchJobID string                 `json:"batchJobId,omitempty"`
	FileID     string                 `json:"fileId,omitempty"`
	Data       map[string]interface{} `json:"data,omitempty"`
}

var logger *Logger

func NewLogger() *Logger {
	levelStr := os.Getenv("LOG_LEVEL")
	if levelStr == "" {
		levelStr = "INFO"
	}

	level := INFO
	switch strings.ToUpper(levelStr) {
	case "ERROR":
		level = ERROR
	case "WARN":
		level = WARN
	case "DEBUG":
		level = DEBUG
	}

	return &Logger{level: level}
}

func (l *Logger) Log(level LogLevel, levelStr, message string, data map[string]interface{}) {
	if level > l.level {
		return
	}

	l.mu.Lock()
	defer l.mu.Unlock()

	entry := LogEntry{
		Timestamp:  time.Now().UTC().Format(time.RFC3339),
		Level:      levelStr,
		Message:    message,
		BatchJobID: os.Getenv("AWS_BATCH_JOB_ID"),
		FileID:     os.Getenv("FILE_ID"),
		Data:       data,
	}

	jsonEntry, _ := json.Marshal(entry)
	fmt.Println(string(jsonEntry))
}

// Processing structures
type TextractResult struct {
	Text       string
	WordCount  int
	LineCount  int
	Confidence float32
	JobID      string
}

type FormattedText struct {
	Formatted  string
	Paragraphs []Paragraph
	Stats      TextStats
}

type Paragraph struct {
	Text      string `json:"text"`
	Type      string `json:"type"`
	WordCount int    `json:"wordCount"`
	CharCount int    `json:"charCount"`
}

type TextStats struct {
	ParagraphCount   int `json:"paragraphCount"`
	SentenceCount    int `json:"sentenceCount"`
	CleanedChars     int `json:"cleanedChars"`
	OriginalChars    int `json:"originalChars"`
	ReductionPercent int `json:"reductionPercent"`
}

type ComprehendResult struct {
	Language             string                          `json:"language"`
	LanguageScore        float32                         `json:"languageScore"`
	Sentiment            *SentimentResult                `json:"sentiment,omitempty"`
	Entities             []EntityResult                  `json:"entities"`
	EntitySummary        map[string][]EntitySummaryItem  `json:"entitySummary"`
	EntityStats          EntityStats                     `json:"entityStats"`
	KeyPhrases           []KeyPhraseResult               `json:"keyPhrases"`
	Syntax               []SyntaxResult                  `json:"syntax"`
	ProcessingTime       float64                         `json:"processingTime"`
	AnalyzedTextLength   int                             `json:"analyzedTextLength"`
	OriginalTextLength   int                             `json:"originalTextLength"`
	Truncated            bool                            `json:"truncated"`
	Error                string                          `json:"error,omitempty"`
}

type SentimentResult struct {
	Sentiment      string                                   `json:"Sentiment"`
	SentimentScore comprehendTypes.SentimentScore          `json:"SentimentScore"`
}

type EntityResult struct {
	Text         string  `json:"Text"`
	Type         string  `json:"Type"`
	Score        float32 `json:"Score"`
	BeginOffset  int32   `json:"BeginOffset"`
	EndOffset    int32   `json:"EndOffset"`
	Length       int32   `json:"Length"`
	Category     string  `json:"Category"`
	Confidence   string  `json:"Confidence"`
}

type EntitySummaryItem struct {
	Text       string  `json:"text"`
	Score      float32 `json:"score"`
	Confidence string  `json:"confidence"`
}

type EntityStats struct {
	TotalEntities          int      `json:"totalEntities"`
	UniqueTypes            []string `json:"uniqueTypes"`
	HighConfidenceEntities int      `json:"highConfidenceEntities"`
	Categories             []string `json:"categories"`
}

type KeyPhraseResult struct {
	Text        string  `json:"Text"`
	Score       float32 `json:"Score"`
	BeginOffset int32   `json:"BeginOffset"`
	EndOffset   int32   `json:"EndOffset"`
}

type SyntaxResult struct {
	Text         string  `json:"Text"`
	PartOfSpeech string  `json:"PartOfSpeech"`
	Score        float32 `json:"Score"`
	BeginOffset  int32   `json:"BeginOffset"`
	EndOffset    int32   `json:"EndOffset"`
}

// AWS clients
var (
	s3Client         *s3.Client
	dynamoClient     *dynamodb.Client
	textractClient   *textract.Client
	comprehendClient *comprehend.Client
)

func init() {
	logger = NewLogger()
}

func main() {
	// Set up signal handling
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGTERM, syscall.SIGINT)

	go func() {
		sig := <-sigChan
		logger.Log(INFO, "INFO", fmt.Sprintf("Received signal: %v, shutting down gracefully", sig), nil)
		os.Exit(0)
	}()

	// Log startup info
	isDev := os.Getenv("NODE_ENV") == "development"
	if isDev || logger.level == DEBUG {
		logger.Log(DEBUG, "DEBUG", "Container startup debug info", map[string]interface{}{
			"goVersion": strings.TrimPrefix(strings.TrimSpace(strings.Split(os.Args[0], " ")[0]), "go"),
			"environment": map[string]string{
				"AWS_BATCH_JOB_ID": os.Getenv("AWS_BATCH_JOB_ID"),
				"S3_BUCKET":        os.Getenv("S3_BUCKET"),
				"S3_KEY":           os.Getenv("S3_KEY"),
				"FILE_ID":          os.Getenv("FILE_ID"),
				"DYNAMODB_TABLE":   os.Getenv("DYNAMODB_TABLE"),
				"AWS_REGION":       os.Getenv("AWS_REGION"),
			},
		})
	} else {
		hasRequiredEnvVars := os.Getenv("S3_BUCKET") != "" && os.Getenv("S3_KEY") != "" &&
			os.Getenv("FILE_ID") != "" && os.Getenv("DYNAMODB_TABLE") != ""
		logger.Log(INFO, "INFO", "OCR Processor starting - batch mode only", map[string]interface{}{
			"hasRequiredEnvVars": hasRequiredEnvVars,
		})
	}

	// Initialize AWS clients
	ctx := context.Background()
	if err := initializeAWSClients(ctx); err != nil {
		logger.Log(ERROR, "ERROR", "Failed to initialize AWS clients", map[string]interface{}{
			"error": err.Error(),
		})
		os.Exit(1)
	}

	// Run batch job with small delay for logging setup
	time.Sleep(100 * time.Millisecond)
	if err := runBatchJob(ctx); err != nil {
		logger.Log(ERROR, "ERROR", "Batch job failed", map[string]interface{}{
			"error": err.Error(),
		})
		os.Exit(1)
	}
}

func initializeAWSClients(ctx context.Context) error {
	cfg, err := config.LoadDefaultConfig(ctx)
	if err != nil {
		return fmt.Errorf("unable to load SDK config: %w", err)
	}

	s3Client = s3.NewFromConfig(cfg)
	dynamoClient = dynamodb.NewFromConfig(cfg)
	textractClient = textract.NewFromConfig(cfg)
	comprehendClient = comprehend.NewFromConfig(cfg)

	return nil
}

func runBatchJob(ctx context.Context) error {
	// Validate required environment variables
	requiredVars := []string{"S3_BUCKET", "S3_KEY", "FILE_ID", "DYNAMODB_TABLE"}
	var missingVars []string
	for _, v := range requiredVars {
		if os.Getenv(v) == "" {
			missingVars = append(missingVars, v)
		}
	}

	if len(missingVars) > 0 {
		logger.Log(ERROR, "ERROR", "Missing required environment variables", map[string]interface{}{
			"missingVars": missingVars,
		})
		return fmt.Errorf("missing required environment variables: %v", missingVars)
	}

	logger.Log(INFO, "INFO", "Starting batch processing", map[string]interface{}{
		"batchJobId": os.Getenv("AWS_BATCH_JOB_ID"),
		"jobQueue":   os.Getenv("AWS_BATCH_JQ_NAME"),
	})

	result, err := processS3File(ctx)
	if err != nil {
		return err
	}

	logger.Log(INFO, "INFO", "Batch job completed successfully", map[string]interface{}{
		"processingDuration": result["processing_duration"],
		"textExtracted":      result["analysis"].(map[string]interface{})["word_count"].(int) > 0,
	})

	return nil
}

func processS3File(ctx context.Context) (map[string]interface{}, error) {
	bucketName := os.Getenv("S3_BUCKET")
	objectKey := os.Getenv("S3_KEY")
	fileID := os.Getenv("FILE_ID")
	dynamoTable := os.Getenv("DYNAMODB_TABLE")

	logger.Log(INFO, "INFO", "Starting file processing", map[string]interface{}{
		"bucket": bucketName,
		"key":    objectKey,
		"fileId": fileID,
		"table":  dynamoTable,
	})

	// Update status to processing
	if err := updateFileStatus(ctx, dynamoTable, fileID, "processing", map[string]interface{}{
		"processing_started": time.Now().UTC().Format(time.RFC3339),
		"batch_job_id":       os.Getenv("AWS_BATCH_JOB_ID"),
	}); err != nil {
		return nil, err
	}

	// Get file metadata
	headResp, err := s3Client.HeadObject(ctx, &s3.HeadObjectInput{
		Bucket: aws.String(bucketName),
		Key:    aws.String(objectKey),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to get S3 object metadata: %w", err)
	}

	fileSize := headResp.ContentLength
	contentType := aws.ToString(headResp.ContentType)

	logger.Log(INFO, "INFO", "File metadata retrieved", map[string]interface{}{
		"size":         fileSize,
		"contentType":  contentType,
		"lastModified": headResp.LastModified,
	})

	// Process with Textract
	startTime := time.Now()
	extractedData, err := processFileWithTextract(ctx, bucketName, objectKey)
	if err != nil {
		updateFileStatus(ctx, dynamoTable, fileID, "failed", map[string]interface{}{
			"error_message": err.Error(),
			"failed_at":     time.Now().UTC().Format(time.RFC3339),
		})
		return nil, err
	}
	textractTime := time.Since(startTime).Seconds()

	logger.Log(INFO, "INFO", "Textract processing completed", map[string]interface{}{
		"processingTimeSeconds": textractTime,
		"wordCount":             extractedData.WordCount,
		"lineCount":             extractedData.LineCount,
		"confidence":            extractedData.Confidence,
	})

	// Format extracted text
	var formattedTextData FormattedText
	textForComprehend := extractedData.Text

	if strings.TrimSpace(extractedData.Text) != "" {
		logger.Log(INFO, "INFO", "Formatting extracted text", nil)
		formattedTextData = formatExtractedText(extractedData.Text)
		if formattedTextData.Formatted != "" {
			textForComprehend = formattedTextData.Formatted
		}

		logger.Log(INFO, "INFO", "Text formatting completed", map[string]interface{}{
			"originalChars": formattedTextData.Stats.OriginalChars,
			"cleanedChars":  formattedTextData.Stats.CleanedChars,
			"paragraphs":    formattedTextData.Stats.ParagraphCount,
			"sentences":     formattedTextData.Stats.SentenceCount,
			"reduction":     fmt.Sprintf("%d%%", formattedTextData.Stats.ReductionPercent),
		})
	}

	// Process with Comprehend
	var comprehendData ComprehendResult
	if strings.TrimSpace(textForComprehend) != "" {
		logger.Log(INFO, "INFO", "Starting Comprehend analysis on formatted text", nil)
		comprehendStartTime := time.Now()
		comprehendData = processTextWithComprehend(ctx, textForComprehend)
		comprehendTime := time.Since(comprehendStartTime).Seconds()

		logger.Log(INFO, "INFO", "Comprehend analysis completed", map[string]interface{}{
			"processingTimeSeconds": comprehendTime,
			"language":              comprehendData.Language,
			"sentiment":             comprehendData.Sentiment,
			"entitiesCount":         len(comprehendData.Entities),
			"keyPhrasesCount":       len(comprehendData.KeyPhrases),
		})
	} else {
		logger.Log(INFO, "INFO", "Skipping Comprehend analysis - no text extracted", nil)
	}

	totalProcessingTime := time.Since(startTime).Seconds()

	// Generate processing results
	processingResults := map[string]interface{}{
		"processed_at":     time.Now().UTC().Format(time.RFC3339),
		"file_size":        fileSize,
		"content_type":     contentType,
		"processing_duration": fmt.Sprintf("%.2f seconds", totalProcessingTime),
		"extracted_text":   extractedData.Text,
		"formatted_text":   formattedTextData.Formatted,
		"text_formatting": map[string]interface{}{
			"paragraphs":     formattedTextData.Paragraphs,
			"stats":          formattedTextData.Stats,
			"hasFormatting":  formattedTextData.Formatted != "",
		},
		"analysis": map[string]interface{}{
			"word_count":      extractedData.WordCount,
			"character_count": len(extractedData.Text),
			"line_count":      extractedData.LineCount,
			"confidence":      extractedData.Confidence,
		},
		"comprehend_analysis": comprehendData,
		"metadata": map[string]interface{}{
			"processor_version": "2.2.0",
			"batch_job_id":      os.Getenv("AWS_BATCH_JOB_ID"),
			"textract_job_id":   extractedData.JobID,
			"textract_duration": fmt.Sprintf("%.2f seconds", textractTime),
			"comprehend_duration": fmt.Sprintf("%.2f seconds", comprehendData.ProcessingTime),
		},
	}

	// Store results
	if err := storeProcessingResults(ctx, fileID, processingResults); err != nil {
		return nil, err
	}

	// Update status to processed
	if err := updateFileStatus(ctx, dynamoTable, fileID, "processed", map[string]interface{}{
		"processing_completed": time.Now().UTC().Format(time.RFC3339),
		"processing_duration":  processingResults["processing_duration"],
	}); err != nil {
		return nil, err
	}

	logger.Log(INFO, "INFO", "File processing completed successfully", map[string]interface{}{
		"processingTimeSeconds": totalProcessingTime,
		"extractedWords":        extractedData.WordCount,
		"extractedLines":        extractedData.LineCount,
		"confidence":            extractedData.Confidence,
		"comprehendLanguage":    comprehendData.Language,
		"comprehendSentiment":   comprehendData.Sentiment,
	})

	return processingResults, nil
}

func processFileWithTextract(ctx context.Context, bucketName, objectKey string) (*TextractResult, error) {
	logger.Log(INFO, "INFO", "Starting Textract document analysis", map[string]interface{}{
		"s3Uri": fmt.Sprintf("s3://%s/%s", bucketName, objectKey),
	})

	// Start document analysis
	startResp, err := textractClient.StartDocumentAnalysis(ctx, &textract.StartDocumentAnalysisInput{
		DocumentLocation: &textractTypes.DocumentLocation{
			S3Object: &textractTypes.S3Object{
				Bucket: aws.String(bucketName),
				Name:   aws.String(objectKey),
			},
		},
		FeatureTypes: []textractTypes.FeatureType{
			textractTypes.FeatureTypeTables,
			textractTypes.FeatureTypeForms,
		},
	})
	if err != nil {
		return nil, fmt.Errorf("failed to start Textract analysis: %w", err)
	}

	jobID := aws.ToString(startResp.JobId)
	logger.Log(INFO, "INFO", "Textract job submitted", map[string]interface{}{
		"textractJobId": jobID,
	})

	// Wait for completion
	maxAttempts := 60
	for attempts := 0; attempts < maxAttempts; attempts++ {
		time.Sleep(5 * time.Second)

		statusResp, err := textractClient.GetDocumentAnalysis(ctx, &textract.GetDocumentAnalysisInput{
			JobId: aws.String(jobID),
		})
		if err != nil {
			return nil, fmt.Errorf("failed to get Textract status: %w", err)
		}

		jobStatus := statusResp.JobStatus
		if attempts%6 == 0 {
			logger.Log(INFO, "INFO", "Waiting for Textract completion", map[string]interface{}{
				"status":      jobStatus,
				"attempt":     attempts,
				"maxAttempts": maxAttempts,
			})
		}

		if jobStatus == textractTypes.JobStatusFailed {
			return nil, fmt.Errorf("Textract job failed: %s", aws.ToString(statusResp.StatusMessage))
		}

		if jobStatus == textractTypes.JobStatusSucceeded {
			break
		}

		if attempts == maxAttempts-1 {
			return nil, fmt.Errorf("Textract job timeout after %d attempts", maxAttempts)
		}
	}

	// Get all results
	var allBlocks []textractTypes.Block
	var nextToken *string
	pageCount := 0

	for {
		resp, err := textractClient.GetDocumentAnalysis(ctx, &textract.GetDocumentAnalysisInput{
			JobId:     aws.String(jobID),
			NextToken: nextToken,
		})
		if err != nil {
			return nil, fmt.Errorf("failed to get Textract results: %w", err)
		}

		allBlocks = append(allBlocks, resp.Blocks...)
		nextToken = resp.NextToken
		pageCount++

		if nextToken == nil {
			break
		}
	}

	logger.Log(DEBUG, "DEBUG", "Textract results retrieved", map[string]interface{}{
		"totalBlocks": len(allBlocks),
		"pages":       pageCount,
	})

	// Extract text
	var extractedText []string
	var totalConfidence float32
	confidenceCount := 0

	for _, block := range allBlocks {
		if block.BlockType == textractTypes.BlockTypeLine && block.Text != nil {
			extractedText = append(extractedText, aws.ToString(block.Text))
			if block.Confidence != nil {
				totalConfidence += aws.ToFloat32(block.Confidence)
				confidenceCount++
			}
		}
	}

	fullText := strings.Join(extractedText, "\n")
	words := strings.Fields(fullText)

	avgConfidence := float32(0)
	if confidenceCount > 0 {
		avgConfidence = totalConfidence / float32(confidenceCount)
	}

	return &TextractResult{
		Text:       fullText,
		WordCount:  len(words),
		LineCount:  len(extractedText),
		Confidence: avgConfidence,
		JobID:      jobID,
	}, nil
}

func formatExtractedText(rawText string) FormattedText {
	if rawText == "" {
		return FormattedText{
			Formatted:  "",
			Paragraphs: []Paragraph{},
			Stats: TextStats{
				ParagraphCount: 0,
				SentenceCount:  0,
				CleanedChars:   0,
			},
		}
	}

	// Fix URLs and emails
	preprocessed := fixURLsAndEmails(rawText)

	// Continue with other preprocessing
	preprocessed = regexp.MustCompile(`\.\s+([A-Z])`).ReplaceAllString(preprocessed, ". $1")
	preprocessed = regexp.MustCompile(`([a-z])\s+([A-Z])`).ReplaceAllString(preprocessed, "$1 $2")
	preprocessed = regexp.MustCompile(`(\w)\s+([,.])`).ReplaceAllString(preprocessed, "$1$2")
	preprocessed = regexp.MustCompile(`([,.!?;:])\s*`).ReplaceAllString(preprocessed, "$1 ")
	preprocessed = regexp.MustCompile(`\n{4,}`).ReplaceAllString(preprocessed, "\n\n\n")
	preprocessed = strings.ReplaceAll(preprocessed, "\r", "")
	preprocessed = strings.ReplaceAll(preprocessed, "\t", " ")

	// Smart line joining
	lines := strings.Split(preprocessed, "\n")
	var processedLines []string
	currentLine := ""

	for _, line := range lines {
		line = strings.TrimSpace(line)

		if line == "" {
			if currentLine != "" {
				processedLines = append(processedLines, currentLine)
				currentLine = ""
			}
			processedLines = append(processedLines, "")
			continue
		}

		isVeryShort := len(line) < 20
		endsWithPunctuation := regexp.MustCompile(`[.!?]$`).MatchString(currentLine)
		startsWithCapital := regexp.MustCompile(`^[A-Z]`).MatchString(line)
		looksLikeHeading := len(line) < 40 && line == strings.ToUpper(line)

		if currentLine != "" && !endsWithPunctuation && !startsWithCapital && !looksLikeHeading && !isVeryShort {
			currentLine += " " + line
		} else {
			if currentLine != "" {
				processedLines = append(processedLines, currentLine)
			}
			currentLine = line
		}
	}

	if currentLine != "" {
		processedLines = append(processedLines, currentLine)
	}

	// Create paragraphs
	var paragraphs []Paragraph
	var currentParagraph []string

	for _, line := range processedLines {
		if line == "" {
			if len(currentParagraph) > 0 {
				text := strings.Join(currentParagraph, " ")
				text = strings.TrimSpace(text)
				if text != "" {
					paragraphs = append(paragraphs, Paragraph{
						Text:      text,
						Type:      "paragraph",
						WordCount: len(strings.Fields(text)),
						CharCount: len(text),
					})
				}
				currentParagraph = []string{}
			}
		} else {
			currentParagraph = append(currentParagraph, line)
		}
	}

	if len(currentParagraph) > 0 {
		text := strings.Join(currentParagraph, " ")
		text = strings.TrimSpace(text)
		if text != "" {
			paragraphs = append(paragraphs, Paragraph{
				Text:      text,
				Type:      "paragraph",
				WordCount: len(strings.Fields(text)),
				CharCount: len(text),
			})
		}
	}

	// Create formatted output
	var formattedParts []string
	for _, p := range paragraphs {
		formattedParts = append(formattedParts, p.Text)
	}
	formatted := strings.Join(formattedParts, "\n\n")

	// Final cleanup
	formatted = fixURLsAndEmails(formatted)
	formatted = regexp.MustCompile(`\s+([,.!?;:])`).ReplaceAllString(formatted, "$1")
	formatted = regexp.MustCompile(`([,.!?;:])(?!\s|$)`).ReplaceAllString(formatted, "$1 ")
	formatted = regexp.MustCompile(` {2,}`).ReplaceAllString(formatted, " ")
	formatted = strings.TrimSpace(formatted)

	// Calculate stats
	sentences := regexp.MustCompile(`[.!?]+`).FindAllString(formatted, -1)
	stats := TextStats{
		ParagraphCount:   len(paragraphs),
		SentenceCount:    len(sentences),
		CleanedChars:     len(formatted),
		OriginalChars:    len(rawText),
		ReductionPercent: int(float64(len(rawText)-len(formatted)) / float64(len(rawText)) * 100),
	}

	return FormattedText{
		Formatted:  formatted,
		Paragraphs: paragraphs,
		Stats:      stats,
	}
}

func fixURLsAndEmails(text string) string {
	// Fix emails
	emailRegex := regexp.MustCompile(`(\w+)\s*@\s*([^\s\n\r\t]+)`)
	text = emailRegex.ReplaceAllStringFunc(text, func(match string) string {
		parts := strings.Split(match, "@")
		if len(parts) == 2 {
			user := strings.TrimSpace(parts[0])
			domain := strings.ReplaceAll(parts[1], " ", "")
			domain = regexp.MustCompile(`\.\s+`).ReplaceAllString(domain, ".")
			return user + "@" + domain
		}
		return match
	})

	// Fix URLs starting with www.
	wwwRegex := regexp.MustCompile(`www\.\s+([^\s\n\r\t]+?)(\s+(?:I|,|\||$))`)
	text = wwwRegex.ReplaceAllStringFunc(text, func(match string) string {
		urlPart := regexp.MustCompile(`www\.\s+`).ReplaceAllString(match, "www.")
		urlPart = regexp.MustCompile(`\.\s+`).ReplaceAllString(urlPart, ".")
		urlPart = regexp.MustCompile(`\s+\.`).ReplaceAllString(urlPart, ".")
		return strings.ReplaceAll(urlPart, " ", "")
	})

	// Fix domain patterns
	text = regexp.MustCompile(`(\w+)\.\s+(\w+)\.\s+(\w+)(?:\s|$|[^\w])`).ReplaceAllString(text, "$1.$2.$3")
	text = regexp.MustCompile(`(\w+)\.\s+(\w+)(?:\s|$|[^\w])`).ReplaceAllString(text, "$1.$2")

	// Fix http:// and https://
	text = regexp.MustCompile(`https?\s*:\s*\/\s*\/\s*`).ReplaceAllStringFunc(text, func(match string) string {
		return strings.ReplaceAll(match, " ", "")
	})

	// Fix TLDs
	tldRegex := regexp.MustCompile(`(\S+)\.\s+(\w{2,3})(?:\s|$|[^\w])`)
	text = tldRegex.ReplaceAllStringFunc(text, func(match string) string {
		parts := regexp.MustCompile(`\.\s+`).Split(match, -1)
		if len(parts) == 2 {
			domain := parts[0]
			tld := strings.TrimSpace(parts[1])
			if regexp.MustCompile(`^(com|net|org|edu|gov|mil|int|nz|au|uk|us|ca|de|fr|jp|cn|io|co|me|info|biz)$`).MatchString(strings.ToLower(tld)) {
				return domain + "." + tld
			}
		}
		return match
	})

	return text
}

func getEntityCategory(entityType string) string {
	categories := map[string]string{
		"PERSON":          "People",
		"LOCATION":        "Places",
		"ORGANIZATION":    "Organizations",
		"COMMERCIAL_ITEM": "Products & Services",
		"EVENT":           "Events",
		"DATE":            "Dates & Times",
		"QUANTITY":        "Numbers & Quantities",
		"TITLE":           "Titles & Positions",
		"OTHER":           "Other",
	}

	if category, ok := categories[entityType]; ok {
		return category
	}
	return "Other"
}

func processTextWithComprehend(ctx context.Context, text string) ComprehendResult {
	const maxLength = 5000
	textToAnalyze := text
	if len(text) > maxLength {
		textToAnalyze = text[:maxLength]
	}

	logger.Log(INFO, "INFO", "Starting Comprehend analysis", map[string]interface{}{
		"originalLength": len(text),
		"analyzedLength": len(textToAnalyze),
		"truncated":      len(text) > maxLength,
	})

	startTime := time.Now()
	result := ComprehendResult{
		OriginalTextLength: len(text),
		AnalyzedTextLength: len(textToAnalyze),
		Truncated:          len(text) > maxLength,
	}

	// Language detection
	langResp, err := comprehendClient.DetectDominantLanguage(ctx, &comprehend.DetectDominantLanguageInput{
		Text: aws.String(textToAnalyze),
	})
	if err != nil {
		logger.Log(WARN, "WARN", "Language detection failed", map[string]interface{}{
			"error": err.Error(),
		})
		result.Language = "unknown"
		result.LanguageScore = 0
	} else if len(langResp.Languages) > 0 {
		result.Language = aws.ToString(langResp.Languages[0].LanguageCode)
		result.LanguageScore = aws.ToFloat32(langResp.Languages[0].Score)
	}

	langCode := result.Language
	if langCode == "unknown" {
		langCode = "en"
	}

	// Sentiment analysis
	sentResp, err := comprehendClient.DetectSentiment(ctx, &comprehend.DetectSentimentInput{
		Text:         aws.String(textToAnalyze),
		LanguageCode: aws.String(langCode),
	})
	if err != nil {
		logger.Log(WARN, "WARN", "Sentiment analysis failed", map[string]interface{}{
			"error": err.Error(),
		})
	} else {
		result.Sentiment = &SentimentResult{
			Sentiment:      string(sentResp.Sentiment),
			SentimentScore: *sentResp.SentimentScore,
		}
	}

	// Entity detection
	entResp, err := comprehendClient.DetectEntities(ctx, &comprehend.DetectEntitiesInput{
		Text:         aws.String(textToAnalyze),
		LanguageCode: aws.String(langCode),
	})
	if err != nil {
		logger.Log(WARN, "WARN", "Entity detection failed", map[string]interface{}{
			"error": err.Error(),
		})
		result.Entities = []EntityResult{}
		result.EntitySummary = make(map[string][]EntitySummaryItem)
	} else {
		result.Entities = make([]EntityResult, len(entResp.Entities))
		result.EntitySummary = make(map[string][]EntitySummaryItem)
		uniqueTypes := make(map[string]bool)
		categories := make(map[string]bool)
		highConfidence := 0

		for i, entity := range entResp.Entities {
			confidence := "Low"
			if aws.ToFloat32(entity.Score) >= 0.8 {
				confidence = "High"
				highConfidence++
			} else if aws.ToFloat32(entity.Score) >= 0.5 {
				confidence = "Medium"
			}

			entityType := string(entity.Type)
			category := getEntityCategory(entityType)
			
			result.Entities[i] = EntityResult{
				Text:        aws.ToString(entity.Text),
				Type:        entityType,
				Score:       aws.ToFloat32(entity.Score),
				BeginOffset: aws.ToInt32(entity.BeginOffset),
				EndOffset:   aws.ToInt32(entity.EndOffset),
				Length:      aws.ToInt32(entity.EndOffset) - aws.ToInt32(entity.BeginOffset),
				Category:    category,
				Confidence:  confidence,
			}

			uniqueTypes[entityType] = true
			categories[category] = true

			if _, ok := result.EntitySummary[entityType]; !ok {
				result.EntitySummary[entityType] = []EntitySummaryItem{}
			}
			result.EntitySummary[entityType] = append(result.EntitySummary[entityType], EntitySummaryItem{
				Text:       aws.ToString(entity.Text),
				Score:      aws.ToFloat32(entity.Score),
				Confidence: confidence,
			})
		}

		var uniqueTypesList []string
		for t := range uniqueTypes {
			uniqueTypesList = append(uniqueTypesList, t)
		}
		var categoriesList []string
		for c := range categories {
			categoriesList = append(categoriesList, c)
		}

		result.EntityStats = EntityStats{
			TotalEntities:          len(result.Entities),
			UniqueTypes:            uniqueTypesList,
			HighConfidenceEntities: highConfidence,
			Categories:             categoriesList,
		}
	}

	// Key phrases
	keyResp, err := comprehendClient.DetectKeyPhrases(ctx, &comprehend.DetectKeyPhrasesInput{
		Text:         aws.String(textToAnalyze),
		LanguageCode: aws.String(langCode),
	})
	if err != nil {
		logger.Log(WARN, "WARN", "Key phrases extraction failed", map[string]interface{}{
			"error": err.Error(),
		})
		result.KeyPhrases = []KeyPhraseResult{}
	} else {
		result.KeyPhrases = make([]KeyPhraseResult, len(keyResp.KeyPhrases))
		for i, phrase := range keyResp.KeyPhrases {
			result.KeyPhrases[i] = KeyPhraseResult{
				Text:        aws.ToString(phrase.Text),
				Score:       aws.ToFloat32(phrase.Score),
				BeginOffset: aws.ToInt32(phrase.BeginOffset),
				EndOffset:   aws.ToInt32(phrase.EndOffset),
			}
		}
	}

	// Syntax analysis
	synResp, err := comprehendClient.DetectSyntax(ctx, &comprehend.DetectSyntaxInput{
		Text:         aws.String(textToAnalyze),
		LanguageCode: aws.String(langCode),
	})
	if err != nil {
		logger.Log(WARN, "WARN", "Syntax analysis failed", map[string]interface{}{
			"error": err.Error(),
		})
		result.Syntax = []SyntaxResult{}
	} else {
		result.Syntax = make([]SyntaxResult, len(synResp.SyntaxTokens))
		for i, token := range synResp.SyntaxTokens {
			result.Syntax[i] = SyntaxResult{
				Text:         aws.ToString(token.Text),
				PartOfSpeech: string(token.PartOfSpeech.Tag),
				Score:        aws.ToFloat32(token.PartOfSpeech.Score),
				BeginOffset:  aws.ToInt32(token.BeginOffset),
				EndOffset:    aws.ToInt32(token.EndOffset),
			}
		}
	}

	result.ProcessingTime = time.Since(startTime).Seconds()
	return result
}

func updateFileStatus(ctx context.Context, tableName, fileID, status string, additionalData map[string]interface{}) error {
	// First get the upload_timestamp
	queryResp, err := dynamoClient.Query(ctx, &dynamodb.QueryInput{
		TableName:              aws.String(tableName),
		KeyConditionExpression: aws.String("file_id = :fileId"),
		ExpressionAttributeValues: map[string]dynamodbTypes.AttributeValue{
			":fileId": &dynamodbTypes.AttributeValueMemberS{Value: fileID},
		},
		Limit: aws.Int32(1),
	})
	if err != nil {
		return fmt.Errorf("failed to query file: %w", err)
	}

	if len(queryResp.Items) == 0 {
		return fmt.Errorf("file with ID %s not found in database", fileID)
	}

	uploadTimestamp := queryResp.Items[0]["upload_timestamp"].(*dynamodbTypes.AttributeValueMemberS).Value

	// Update the item
	updateExpr := "SET processing_status = :status, last_updated = :updated"
	exprAttrValues := map[string]dynamodbTypes.AttributeValue{
		":status":  &dynamodbTypes.AttributeValueMemberS{Value: status},
		":updated": &dynamodbTypes.AttributeValueMemberS{Value: time.Now().UTC().Format(time.RFC3339)},
	}

	// Add additional data
	for key, value := range additionalData {
		attrName := fmt.Sprintf(":val%s", key)
		updateExpr += fmt.Sprintf(", %s = %s", key, attrName)
		
		switch v := value.(type) {
		case string:
			exprAttrValues[attrName] = &dynamodbTypes.AttributeValueMemberS{Value: v}
		case int:
			exprAttrValues[attrName] = &dynamodbTypes.AttributeValueMemberN{Value: fmt.Sprintf("%d", v)}
		case float64:
			exprAttrValues[attrName] = &dynamodbTypes.AttributeValueMemberN{Value: fmt.Sprintf("%f", v)}
		default:
			jsonBytes, _ := json.Marshal(v)
			exprAttrValues[attrName] = &dynamodbTypes.AttributeValueMemberS{Value: string(jsonBytes)}
		}
	}

	_, err = dynamoClient.UpdateItem(ctx, &dynamodb.UpdateItemInput{
		TableName: aws.String(tableName),
		Key: map[string]dynamodbTypes.AttributeValue{
			"file_id":          &dynamodbTypes.AttributeValueMemberS{Value: fileID},
			"upload_timestamp": &dynamodbTypes.AttributeValueMemberS{Value: uploadTimestamp},
		},
		UpdateExpression:          aws.String(updateExpr),
		ExpressionAttributeValues: exprAttrValues,
	})

	if err != nil {
		logger.Log(ERROR, "ERROR", "Failed to update file status", map[string]interface{}{
			"fileId": fileID,
			"status": status,
			"error":  err.Error(),
		})
		return err
	}

	logger.Log(DEBUG, "DEBUG", "DynamoDB status updated", map[string]interface{}{
		"fileId": fileID,
		"status": status,
	})
	return nil
}

func storeProcessingResults(ctx context.Context, fileID string, results map[string]interface{}) error {
	resultsTable := strings.Replace(os.Getenv("DYNAMODB_TABLE"), "-file-metadata", "-processing-results", 1)

	item := map[string]dynamodbTypes.AttributeValue{
		"file_id": &dynamodbTypes.AttributeValueMemberS{Value: fileID},
	}

	// Convert results to DynamoDB attributes
	for key, value := range results {
		attrValue, err := attributeValueFromInterface(value)
		if err != nil {
			logger.Log(WARN, "WARN", "Failed to convert attribute", map[string]interface{}{
				"key":   key,
				"error": err.Error(),
			})
			continue
		}
		item[key] = attrValue
	}

	_, err := dynamoClient.PutItem(ctx, &dynamodb.PutItemInput{
		TableName: aws.String(resultsTable),
		Item:      item,
	})

	if err != nil {
		logger.Log(ERROR, "ERROR", "Failed to store processing results", map[string]interface{}{
			"fileId": fileID,
			"error":  err.Error(),
		})
		return err
	}

	logger.Log(DEBUG, "DEBUG", "Processing results stored", map[string]interface{}{
		"fileId": fileID,
		"table":  resultsTable,
	})
	return nil
}

func attributeValueFromInterface(v interface{}) (dynamodbTypes.AttributeValue, error) {
	switch value := v.(type) {
	case string:
		return &dynamodbTypes.AttributeValueMemberS{Value: value}, nil
	case int:
		return &dynamodbTypes.AttributeValueMemberN{Value: fmt.Sprintf("%d", value)}, nil
	case int64:
		return &dynamodbTypes.AttributeValueMemberN{Value: fmt.Sprintf("%d", value)}, nil
	case float32:
		return &dynamodbTypes.AttributeValueMemberN{Value: fmt.Sprintf("%f", value)}, nil
	case float64:
		return &dynamodbTypes.AttributeValueMemberN{Value: fmt.Sprintf("%f", value)}, nil
	case bool:
		return &dynamodbTypes.AttributeValueMemberBOOL{Value: value}, nil
	case []string:
		items := make([]dynamodbTypes.AttributeValue, len(value))
		for i, s := range value {
			items[i] = &dynamodbTypes.AttributeValueMemberS{Value: s}
		}
		return &dynamodbTypes.AttributeValueMemberL{Value: items}, nil
	case map[string]interface{}:
		m := make(map[string]dynamodbTypes.AttributeValue)
		for k, v := range value {
			attr, err := attributeValueFromInterface(v)
			if err != nil {
				continue
			}
			m[k] = attr
		}
		return &dynamodbTypes.AttributeValueMemberM{Value: m}, nil
	default:
		// For complex types, marshal to JSON
		jsonBytes, err := json.Marshal(value)
		if err != nil {
			return nil, err
		}
		return &dynamodbTypes.AttributeValueMemberS{Value: string(jsonBytes)}, nil
	}
}