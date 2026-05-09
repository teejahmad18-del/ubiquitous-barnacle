import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email configuration
SENDER_EMAIL = "dahmadu071@gmail.com"
APP_PASSWORD = "gahw bjtb wnai frch"
RECEIVER_EMAIL = "bettyallenbia502@gmail.com"

def get_folders_current_directory():
    """
    Get only the folders in the current directory with their full paths.
    
    Returns:
        list: List of full folder paths in current directory
    """
    current_dir = os.getcwd()
    folders = []
    
    try:
        # List all items in current directory
        for item in os.listdir(current_dir):
            full_path = os.path.join(current_dir, item)
            # Check if it's a directory
            if os.path.isdir(full_path):
                folders.append(full_path)
        
        # Sort alphabetically
        folders.sort()
                
    except PermissionError:
        print(f"Permission denied: {current_dir}")
    except Exception as e:
        print(f"Error accessing {current_dir}: {e}")
    
    return folders, current_dir

def format_folders_for_email(folders, current_dir):
    """
    Format the folder list into a readable string with full paths.
    
    Args:
        folders (list): List of full folder paths
        current_dir (str): Current directory path
    
    Returns:
        str: Formatted string of folders with full paths
    """
    formatted_text = f"Current Directory: {current_dir}\n"
    formatted_text += "=" * 50 + "\n\n"
    formatted_text += "Folders with Full Paths:\n\n"
    
    for i, folder in enumerate(folders, 1):
        formatted_text += f"{i}. {folder}\n"
    
    formatted_text += f"\n{'=' * 50}\n"
    formatted_text += f"Total folders found: {len(folders)}\n"
    
    return formatted_text

def send_email(subject, body):
    """
    Send an email with the folder list.
    
    Args:
        subject (str): Email subject
        body (str): Email body text
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        
        # Attach body
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent successfully to {RECEIVER_EMAIL}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("Authentication failed. Check your email and app password.")
        return False
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def main():
    """
    Main function to find folders in current directory and send via email.
    """
    # Get folders from current directory only
    folders, current_dir = get_folders_current_directory()
    
    if not folders:
        print(f"No folders found in {current_dir}")
        # Send email anyway to notify
        subject = f"No Folders Found - {current_dir}"
        email_body = f"No folders were found in the current directory:\n{current_dir}"
    else:
        print(f"Found {len(folders)} folders in {current_dir}")
        # Format for email
        email_body = format_folders_for_email(folders, current_dir)
        subject = f"Folder List - {current_dir} ({len(folders)} folders found)"
    
    # Print folders with full paths to console
    print("\n" + "="*50)
    print(f"Current Directory: {current_dir}")
    print("="*50)
    print("\nFolders with Full Paths:\n")
    for i, folder in enumerate(folders, 1):
        print(f"{i}. {folder}")
    print(f"\nTotal: {len(folders)} folders")
    
    # Send email
    print("\nSending email...")
    success = send_email(subject, email_body)
    
    if success:
        print("Process completed successfully!")
    else:
        print("Email sending failed.")

if __name__ == "__main__":
    main()
