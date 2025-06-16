#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Starting Bot Setup Script ---"

# 1. System Dependency Installation (for Debian/Ubuntu)
# This installs Tesseract (the OCR engine), Python's package manager, and virtual environment tool.
echo "Updating package list and installing system dependencies..."
sudo apt-get update
sudo apt-get install -y tesseract-ocr python3-pip python3-venv

# 2. Python Virtual Environment Setup
# Creating a virtual environment is best practice to isolate project dependencies.
echo "Creating Python virtual environment in 'venv' directory..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
else
    echo "Virtual environment 'venv' already exists. Skipping creation."
fi


# 3. Installing Python Dependencies
echo "Activating virtual environment and installing Python packages from requirements.txt..."
source venv/bin/activate
pip install -r requirements.txt
deactivate

# 4. Create the .env file if it doesn't exist
# This file will hold your secret tokens.
if [ ! -f ".env" ]; then
    echo "Creating .env file for your secrets..."
    touch .env
    echo "BOT_TOKEN=\"7864369579:AAHJUdTOp-2FngRggPaqmBSg5FIudHE_f3M\"" >> .env
    echo "BOT_2_TOKEN=\"7775302991:AAGhN0WzRQ7FNu4z_TJkOTPU6peAPZuMlnU\"" >> .env
    echo "ADMIN_CHAT_ID=\"1732455712\"" >> .env
    echo "BOT_2_ADMIN_CHAT_ID=\"1732455712\"" >> .env
else
    echo ".env file already exists. Skipping creation."
fi

# 5. Final Instructions
echo ""
echo "✅ --- Setup Complete! --- ✅"
echo ""
echo "IMPORTANT: Open the '.env' file and replace the placeholder values with your real bot tokens and chat IDs."
echo "You can edit the file with the command: nano .env"
echo ""
echo "After editing, run the bot using these two commands:"
echo ""
echo "source venv/bin/activate"
echo "python3 main.py"
echo ""