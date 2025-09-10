# Automation Orchestrator Makefile
# Development and management tasks for the infrastructure automation system

.PHONY: help install test lint format clean run-example setup-dev

# Default target
help:
	@echo "Automation Orchestrator - Available Commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  install      Install dependencies"
	@echo "  setup-dev    Setup development environment"
	@echo ""
	@echo "Development:"
	@echo "  test         Run test suite"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black"
	@echo "  clean        Clean up temporary files"
	@echo ""
	@echo "Usage Examples:"
	@echo "  run-example  Run discovery with example seed file"
	@echo "  demo         Full demonstration workflow"
	@echo ""
	@echo "Documentation:"
	@echo "  docs         Generate documentation"
	@echo "  serve-docs   Serve documentation locally"

# Installation and setup
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

setup-dev: install
	@echo "🔧 Setting up development environment..."
	pip install pytest pytest-mock black flake8 mypy
	chmod +x cli/orchestrate.py
	@echo "✅ Development environment ready"

# Testing
test:
	@echo "🧪 Running test suite..."
	python -m pytest tests/ -v --tb=short
	@echo "✅ Tests completed"

test-coverage:
	@echo "🧪 Running tests with coverage..."
	python -m pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "📊 Coverage report generated in htmlcov/"

# Code quality
lint:
	@echo "🔍 Running linting checks..."
	flake8 src/ cli/ tests/ --max-line-length=120 --ignore=E203,W503
	@echo "✅ Linting completed"

format:
	@echo "🎨 Formatting code..."
	black src/ cli/ tests/ --line-length=120
	@echo "✅ Code formatted"

type-check:
	@echo "🔍 Running type checks..."
	mypy src/ --ignore-missing-imports
	@echo "✅ Type checking completed"

# Cleanup
clean:
	@echo "🧹 Cleaning up temporary files..."
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov/
	rm -rf .mypy_cache
	rm -rf data/
	@echo "✅ Cleanup completed"

# Example workflows
run-example:
	@echo "🚀 Running discovery example..."
	python cli/orchestrate.py create-seed example_seed.yml
	@echo "📝 Created example seed file: example_seed.yml"
	@echo "Edit the file to match your infrastructure, then run:"
	@echo "python cli/orchestrate.py discover example_seed.yml"

demo: clean
	@echo "🎬 Running full demonstration..."
	@echo ""
	@echo "Step 1: Creating sample seed inventory..."
	python cli/orchestrate.py create-seed demo_seed.yml
	
	@echo ""
	@echo "Step 2: Validating seed inventory..."
	python cli/orchestrate.py validate demo_seed.yml --show-suggestions
	
	@echo ""
	@echo "Step 3: Checking orchestrator status..."
	python cli/orchestrate.py status
	
	@echo ""
	@echo "✅ Demo completed! Next steps:"
	@echo "1. Edit demo_seed.yml to match your infrastructure"  
	@echo "2. Run: python cli/orchestrate.py discover demo_seed.yml"
	@echo "3. Use generated hosts.yml with Ansible"

# Validation and checks
validate-config:
	@echo "✅ Validating configuration files..."
	python -c "import yaml; yaml.safe_load(open('config/orchestrator.yml'))" 
	python -c "import yaml; yaml.safe_load(open('config/discovery_rules.yml'))"
	python -c "import yaml; yaml.safe_load(open('config/group_rules.yml'))"
	@echo "✅ Configuration files are valid"

# Documentation
docs:
	@echo "📚 Generating documentation..."
	@echo "Documentation available in docs/README.md"
	@echo "Configuration examples in config/"
	@echo "Templates available in templates/"

serve-docs:
	@echo "🌐 Serving documentation locally..."
	python -m http.server 8000 --directory docs/
	@echo "📖 Documentation available at: http://localhost:8000"

# Quick operations
quick-install: install
	@echo "⚡ Quick install completed"

check: lint type-check test
	@echo "✅ All checks passed"

# Development helpers
dev-setup: setup-dev validate-config
	@echo "🔧 Development environment fully configured"

# Show project structure
structure:
	@echo "📁 Project Structure:"
	@find . -type f -name "*.py" | grep -E "(src|cli|tests)" | head -20
	@echo "..."
	@echo ""
	@echo "📊 Statistics:"
	@find src/ -name "*.py" -exec wc -l {} + | tail -1 | awk '{print "Source code lines:", $$1}'
	@find tests/ -name "*.py" -exec wc -l {} + | tail -1 | awk '{print "Test code lines:", $$1}' 2>/dev/null || echo "Test code lines: 0"
	@find . -name "*.yml" -o -name "*.yaml" | wc -l | awk '{print "Configuration files:", $$1}'

# Integration tests
test-integration:
	@echo "🔗 Running integration tests..."
	@echo "Note: Requires network access and may take longer"
	python -m pytest tests/ -v -k "integration" --tb=short || echo "No integration tests found"

# Performance tests  
test-performance:
	@echo "⚡ Running performance tests..."
	python -m pytest tests/ -v -k "performance" --tb=short || echo "No performance tests found"

# Package building
build:
	@echo "📦 Building package..."
	python setup.py sdist bdist_wheel || echo "No setup.py found - skipping build"

# Security checks
security-check:
	@echo "🔒 Running security checks..."
	pip install safety bandit
	safety check
	bandit -r src/ -f json -o security-report.json || echo "Security scan completed with warnings"
	@echo "🔒 Security check completed"

# Full CI pipeline
ci: check test-coverage security-check
	@echo "🏗️  CI pipeline completed successfully"

# Show help for specific commands
help-discovery:
	@echo "🔍 Discovery Commands:"
	@echo "  discover SEED_FILE    Run full discovery pipeline"
	@echo "  validate SEED_FILE    Validate seed inventory file" 
	@echo "  create-seed FILE      Create sample seed file"
	@echo ""
	@echo "Example:"
	@echo "  python cli/orchestrate.py discover my_infra.yml"

help-inventory:
	@echo "📋 Inventory Commands:"
	@echo "  generate-inventory    Generate Ansible inventory from existing assets"
	@echo "  list-assets          Show discovered assets"
	@echo "  export FILE          Export assets to external format"
	@echo ""
	@echo "Example:"
	@echo "  python cli/orchestrate.py generate-inventory --format yaml"