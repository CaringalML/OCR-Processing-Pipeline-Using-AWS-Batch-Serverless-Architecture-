# DigitizePro Makefile - Structure & Dependencies Only
# Run this from inside the digitize-pro directory

# Colors
GREEN = \033[0;32m
BLUE = \033[0;34m
YELLOW = \033[1;33m
NC = \033[0m

.PHONY: help setup install-deps setup-tailwind create-dirs all

all: setup

help:
	@echo "$(BLUE)DigitizePro Project Structure Setup$(NC)"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup       - Install deps, setup Tailwind, create directories"
	@echo "  make install-deps - Install dependencies only"
	@echo "  make setup-tailwind - Setup Tailwind CSS only"  
	@echo "  make create-dirs - Create directory structure only"

setup: install-deps setup-tailwind create-dirs
	@echo ""
	@echo "$(GREEN)✅ Setup complete!$(NC)"
	@echo "$(BLUE)Directory structure and dependencies ready for development.$(NC)"

install-deps:
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@npm install lucide-react
	@npm install react-router-dom
	@npm install axios
	@npm uninstall tailwindcss || true
	@npm install -D tailwindcss@^3.4.0 postcss autoprefixer
	@echo "$(GREEN)✅ Dependencies installed$(NC)"
	@echo "$(YELLOW)📦 Installed: lucide-react, react-router-dom, axios, tailwindcss@3.4.0$(NC)"

setup-tailwind:
	@echo "$(BLUE)Setting up Tailwind CSS...$(NC)"
	@npx tailwindcss init -p
	@echo "$(BLUE)Updating Tailwind configuration...$(NC)"
	@echo "/** @type {import('tailwindcss').Config} */" > tailwind.config.js
	@echo "module.exports = {" >> tailwind.config.js
	@echo "  content: [" >> tailwind.config.js
	@echo "    \"./src/**/*.{js,jsx,ts,tsx}\"," >> tailwind.config.js
	@echo "  ]," >> tailwind.config.js
	@echo "  theme: {" >> tailwind.config.js
	@echo "    extend: {}," >> tailwind.config.js
	@echo "  }," >> tailwind.config.js
	@echo "  plugins: []," >> tailwind.config.js
	@echo "}" >> tailwind.config.js
	@echo "$(BLUE)Updating CSS file...$(NC)"
	@echo "@tailwind base;" > src/index.css
	@echo "@tailwind components;" >> src/index.css
	@echo "@tailwind utilities;" >> src/index.css
	@echo "" >> src/index.css
	@echo "/* Custom styles */" >> src/index.css
	@echo "body {" >> src/index.css
	@echo "  margin: 0;" >> src/index.css
	@echo "  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen'," >> src/index.css
	@echo "    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue'," >> src/index.css
	@echo "    sans-serif;" >> src/index.css
	@echo "  -webkit-font-smoothing: antialiased;" >> src/index.css
	@echo "  -moz-osx-font-smoothing: grayscale;" >> src/index.css
	@echo "}" >> src/index.css
	@echo "$(GREEN)✅ Tailwind CSS configured$(NC)"

create-dirs:
	@echo "$(BLUE)Creating directory structure...$(NC)"
	@mkdir -p src/components/common/Button
	@mkdir -p src/components/common/Modal
	@mkdir -p src/components/common/Header
	@mkdir -p src/components/common/Sidebar
	@mkdir -p src/components/dashboard/StatsCard
	@mkdir -p src/components/dashboard/ActivityFeed
	@mkdir -p src/components/dashboard/QuickActions
	@mkdir -p src/components/dashboard/StorageOverview
	@mkdir -p src/components/upload/UploadArea
	@mkdir -p src/components/upload/MetadataForm
	@mkdir -p src/components/upload/UploadQueue
	@mkdir -p src/components/upload/DocumentEditor/DocumentPreview
	@mkdir -p src/components/upload/DocumentEditor/TextEditor
	@mkdir -p src/components/inventory/FilterBar
	@mkdir -p src/components/inventory/InventoryTable
	@mkdir -p src/components/search/SearchInput
	@mkdir -p src/components/search/SearchResults
	@mkdir -p src/components/recycle/DeletedItem
	@mkdir -p src/hooks
	@mkdir -p src/context
	@mkdir -p src/services
	@mkdir -p src/utils
	@mkdir -p src/styles
	@mkdir -p src/data
	@touch src/components/common/Button/Button.jsx
	@touch src/components/common/Button/Button.css
	@touch src/components/common/Modal/Modal.jsx
	@touch src/components/common/Modal/Modal.css
	@touch src/components/common/Header/Header.jsx
	@touch src/components/common/Header/Header.css
	@touch src/components/common/Sidebar/Sidebar.jsx
	@touch src/components/common/Sidebar/Sidebar.css
	@touch src/components/dashboard/Dashboard.jsx
	@touch src/components/dashboard/Dashboard.css
	@touch src/components/dashboard/StatsCard/StatsCard.jsx
	@touch src/components/dashboard/StatsCard/StatsCard.css
	@touch src/components/dashboard/ActivityFeed/ActivityFeed.jsx
	@touch src/components/dashboard/ActivityFeed/ActivityFeed.css
	@touch src/components/dashboard/QuickActions/QuickActions.jsx
	@touch src/components/dashboard/QuickActions/QuickActions.css
	@touch src/components/dashboard/StorageOverview/StorageOverview.jsx
	@touch src/components/dashboard/StorageOverview/StorageOverview.css
	@touch src/components/upload/Upload.jsx
	@touch src/components/upload/Upload.css
	@touch src/components/upload/UploadArea/UploadArea.jsx
	@touch src/components/upload/UploadArea/UploadArea.css
	@touch src/components/upload/MetadataForm/MetadataForm.jsx
	@touch src/components/upload/MetadataForm/MetadataForm.css
	@touch src/components/upload/UploadQueue/UploadQueue.jsx
	@touch src/components/upload/UploadQueue/UploadQueue.css
	@touch src/components/upload/DocumentEditor/DocumentEditor.jsx
	@touch src/components/upload/DocumentEditor/DocumentEditor.css
	@touch src/components/upload/DocumentEditor/DocumentPreview/DocumentPreview.jsx
	@touch src/components/upload/DocumentEditor/DocumentPreview/DocumentPreview.css
	@touch src/components/upload/DocumentEditor/TextEditor/TextEditor.jsx
	@touch src/components/upload/DocumentEditor/TextEditor/TextEditor.css
	@touch src/components/inventory/Inventory.jsx
	@touch src/components/inventory/Inventory.css
	@touch src/components/inventory/FilterBar/FilterBar.jsx
	@touch src/components/inventory/FilterBar/FilterBar.css
	@touch src/components/inventory/InventoryTable/InventoryTable.jsx
	@touch src/components/inventory/InventoryTable/InventoryTable.css
	@touch src/components/search/Search.jsx
	@touch src/components/search/Search.css
	@touch src/components/search/SearchInput/SearchInput.jsx
	@touch src/components/search/SearchInput/SearchInput.css
	@touch src/components/search/SearchResults/SearchResults.jsx
	@touch src/components/search/SearchResults/SearchResults.css
	@touch src/components/recycle/RecycleBin.jsx
	@touch src/components/recycle/RecycleBin.css
	@touch src/components/recycle/DeletedItem/DeletedItem.jsx
	@touch src/components/recycle/DeletedItem/DeletedItem.css
	@touch src/hooks/useLocalStorage.js
	@touch src/hooks/useDocuments.js
	@touch src/hooks/useUpload.js
	@touch src/hooks/useSearch.js
	@touch src/context/AppContext.js
	@touch src/context/DocumentContext.js
	@touch src/context/UploadContext.js
	@touch src/services/api.js
	@touch src/services/documentService.js
	@touch src/services/uploadService.js
	@touch src/services/searchService.js
	@touch src/utils/constants.js
	@touch src/utils/helpers.js
	@touch src/utils/formatters.js
	@touch src/utils/validators.js
	@touch src/styles/globals.css
	@touch src/styles/variables.css
	@touch src/styles/themes.css
	@touch src/data/mockData.js
	@touch src/data/sampleDocuments.js
	@echo "$(GREEN)✅ Directory structure created$(NC)"
	@echo "$(YELLOW)📁 Created $(shell find src -name "*.jsx" -o -name "*.js" -o -name "*.css" | wc -l) component files$(NC)"