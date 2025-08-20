# 📄 Digitize-Pro - OCR Document Management Frontend

A modern React-based frontend application for managing document OCR processing, editing, and inventory management.

## 🚀 Features

### Document Upload
- **Drag & Drop Interface** - Intuitive file upload with visual feedback
- **Batch Upload** - Upload multiple documents simultaneously
- **Metadata Management** - Add rich metadata (title, author, publication, tags, etc.)
- **File Validation** - Automatic validation of file types (PDF, TIFF, JPG, PNG) and sizes (max 500MB)
- **Progress Tracking** - Real-time upload progress indicators

### Upload Queue
- **Unified Document List** - Single view for all documents (uploaded, processing, completed)
- **Status Indicators** - Color-coded status badges for each processing stage
- **Progress Bars** - Visual progress tracking for document processing
- **AWS-Style Refresh** - Circular refresh button with loading states
- **Smart Deduplication** - No duplicate rows after document completion
- **Quality Scores** - OCR confidence scores displayed for processed documents

### Document Editor
- **Side-by-Side View** - Original document image alongside extracted text
- **Text Editing** - Edit OCR extracted text with full control
- **Text Type Toggle** - Switch between formatted and AI-refined text
- **Undo/Redo** - Full edit history with undo/redo functionality
- **Document Finalization** - Finalize documents to move to inventory
- **Success Modals** - Custom Tailwind modals with auto-navigation

### Inventory Management
- **Finalized Documents** - View all completed and finalized documents
- **Document Preview** - Quick preview of document content
- **Metadata Display** - View all document metadata and processing details
- **Edit Capabilities** - Edit finalized documents with reason tracking
- **Search & Filter** - Find documents quickly with search functionality

### Document Search
- **Full-Text Search** - Search across all document content
- **Fuzzy Matching** - Find documents even with typos (70-80% accuracy)
- **Advanced Filters** - Filter by author, publication, date, tags
- **Relevance Ranking** - Results sorted by relevance score
- **Snippet Preview** - See matching text snippets in search results

## 🛠️ Installation

### Prerequisites
- Node.js 16+ and npm/yarn
- AWS API Gateway endpoint URL
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Quick Start

1. **Clone the repository**
```bash
git clone <repository-url>
cd OCR-AWS-Batch-Serverless-Python/digitize-pro
```

2. **Install dependencies**
```bash
npm install
# or
yarn install
```

3. **Configure environment**
```bash
# Create .env file from example
cp .env.example .env

# Edit .env and add your API Gateway URL
REACT_APP_API_GATEWAY_URL=https://your-api-gateway.execute-api.region.amazonaws.com
```

4. **Start development server**
```bash
npm start
# or
yarn start
```

The application will open at `http://localhost:3000`

## 📁 Project Structure

```
digitize-pro/
├── public/               # Static assets
├── src/
│   ├── components/       # React components
│   │   ├── edit/        # Document editing components
│   │   │   └── DocumentEdit.jsx
│   │   ├── inventory/   # Inventory management
│   │   │   └── Inventory.jsx
│   │   ├── layout/      # Layout components
│   │   │   ├── Header.jsx
│   │   │   └── Sidebar.jsx
│   │   ├── search/      # Search functionality
│   │   │   └── Search.jsx
│   │   ├── upload/      # Upload interface
│   │   │   └── Upload.jsx
│   │   └── view/        # Document viewing
│   │       └── DocumentView.jsx
│   ├── hooks/           # Custom React hooks
│   │   └── useDocuments.js
│   ├── services/        # API service layer
│   │   ├── documentService.js
│   │   └── uploadService.js
│   ├── styles/          # CSS and styling
│   ├── utils/           # Utility functions
│   ├── App.js           # Main application component
│   └── index.js         # Application entry point
├── .env.example         # Environment variables template
├── package.json         # Dependencies and scripts
└── README.md           # This file
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Required
REACT_APP_API_GATEWAY_URL=https://your-api-gateway.execute-api.region.amazonaws.com

# Optional
REACT_APP_ENVIRONMENT=development
REACT_APP_MAX_FILE_SIZE=524288000  # 500MB in bytes
REACT_APP_ALLOWED_FILE_TYPES=.pdf,.tiff,.tif,.jpg,.jpeg,.png
```

### API Service Configuration

The application uses two main service modules:

- **documentService.js** - Handles document CRUD operations
- **uploadService.js** - Manages file uploads and validation

## 🎨 UI Components

### Key Components

#### Upload Component (`Upload.jsx`)
- Drag-and-drop file upload area
- Metadata form with validation
- Upload queue management
- Progress tracking
- File type/size validation

#### DocumentEdit Component (`DocumentEdit.jsx`)
- Document image viewer
- Text editor with undo/redo
- Text type selector (formatted/refined)
- Finalization workflow
- Success modal implementation

#### Inventory Component (`Inventory.jsx`)
- Grid/list view toggle
- Document cards with metadata
- Quick actions (view, edit, delete)
- Search and filter bar
- Pagination controls

#### Search Component (`Search.jsx`)
- Search input with debouncing
- Advanced filter panel
- Results list with snippets
- Fuzzy search toggle
- Export functionality

## 🚀 Deployment

### Production Build

```bash
# Create optimized production build
npm run build
# or
yarn build
```

### Deploy to AWS S3

```bash
# Create S3 bucket for hosting
aws s3 mb s3://your-frontend-bucket

# Configure bucket for static website hosting
aws s3 website s3://your-frontend-bucket \
  --index-document index.html \
  --error-document error.html

# Upload build files
aws s3 sync build/ s3://your-frontend-bucket --delete

# Set public read permissions
aws s3api put-bucket-policy --bucket your-frontend-bucket \
  --policy file://bucket-policy.json
```

### Deploy with CloudFront CDN

```bash
# Create CloudFront distribution
aws cloudfront create-distribution \
  --origin-domain-name your-frontend-bucket.s3.amazonaws.com \
  --default-root-object index.html

# Invalidate cache after updates
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

## 🧪 Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run tests in watch mode
npm test -- --watchAll
```

## 🐛 Troubleshooting

### Common Issues

#### CORS Errors
- Ensure API Gateway has CORS enabled
- Check allowed origins include your frontend URL
- Verify headers are properly configured

#### Upload Failures
- Check file size limits (default 500MB)
- Verify file types are allowed
- Ensure API endpoint is accessible

#### Processing Status Not Updating
- Check WebSocket/polling connections
- Verify API returns correct status codes
- Check browser console for errors

## 📝 Recent Updates

### August 2025
- ✅ Fixed duplicate row issue in upload queue
- ✅ Implemented custom success modal for finalization
- ✅ Added AWS-style circular refresh button
- ✅ Removed problematic draft functionality
- ✅ Enhanced navigation with proper routing
- ✅ Improved progress bar visualization
- ✅ Fixed view button for finalized documents

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is part of the OCR-AWS-Batch-Serverless-Python system and follows the same MIT License.

## 👥 Authors

- **Martin Lawrence Caringal** - Initial development and architecture

## 🙏 Acknowledgments

- React team for the excellent framework
- Tailwind CSS for the utility-first CSS framework
- Lucide React for the beautiful icons
- AWS for the backend infrastructure

---

*Built with React, Tailwind CSS, and ❤️*