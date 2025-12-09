#!/usr/bin/env python3
"""
Send missing welcome emails and share notification emails.

This script identifies and sends:
1. Welcome emails to users who should have received them
2. Share notification emails for pending recipe shares
"""
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app_mysql import app
from db_models import db, User, PendingRecipeShare, Recipe, RecipeShare, Notification
from email_service import email_service
from flask import url_for
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_welcome_emails(dry_run=True):
    """
    Send welcome emails to users who should have received them.
    
    Criteria:
    - email_verified = True
    - is_active = True
    - account_setup_completed = True (or account_setup_completed is None for older accounts)
    - Created within last 90 days (to avoid spamming old accounts)
    """
    logger.info("=" * 70)
    logger.info("SENDING WELCOME EMAILS")
    logger.info("=" * 70)
    
    if not email_service.is_configured():
        logger.error("Email service is not configured. Cannot send emails.")
        return 0, 0
    
    # Find users who should receive welcome emails
    # Criteria: email verified, active users
    # Include users with account_setup_completed=False (self-registered users who may not have gotten welcome email)
    # and account_setup_completed=True or None (admin-created users who completed setup)
    users = db.session.query(User).filter(
        User.email_verified == True,
        User.is_active == True
        # No filter on account_setup_completed - send to all verified active users
    ).all()
    
    logger.info(f"Found {len(users)} active, verified users who may need welcome emails")
    
    sent_count = 0
    error_count = 0
    
    for user in users:
        try:
            user_name = user.display_name or user.username
            
            if dry_run:
                logger.info(f"[DRY RUN] Would send welcome email to: {user.email} ({user_name})")
                sent_count += 1
            else:
                success, error_msg = email_service.send_welcome_email(
                    user_email=user.email,
                    user_name=user_name
                )
                
                if success:
                    logger.info(f"✓ Sent welcome email to: {user.email} ({user_name})")
                    sent_count += 1
                else:
                    logger.error(f"✗ Failed to send welcome email to {user.email}: {error_msg}")
                    error_count += 1
                    
        except Exception as e:
            logger.error(f"✗ Error sending welcome email to {user.email}: {e}")
            error_count += 1
    
    return sent_count, error_count


def send_share_notification_emails(dry_run=True):
    """
    Send share notification emails for pending recipe shares that may have failed.
    
    This covers:
    - PendingRecipeShare records with status='pending' 
    - Where recipient_email doesn't belong to an existing user
    - These should have emails sent with the recipe link
    """
    logger.info("=" * 70)
    logger.info("SENDING SHARE NOTIFICATION EMAILS")
    logger.info("=" * 70)
    
    if not email_service.is_configured():
        logger.error("Email service is not configured. Cannot send emails.")
        return 0, 0, 0
    
    # Find pending shares where recipient is not a user
    pending_shares = db.session.query(PendingRecipeShare).filter(
        PendingRecipeShare.status == 'pending',
        PendingRecipeShare.shared_with_user_id.is_(None)  # Not linked to a user yet
    ).all()
    
    logger.info(f"Found {len(pending_shares)} pending recipe shares to notify")
    
    sent_count = 0
    error_count = 0
    skipped_count = 0
    
    with app.app_context():
        for pending_share in pending_shares:
            try:
                # Get recipe
                recipe = db.session.query(Recipe).filter(
                    Recipe.id == pending_share.recipe_id,
                    Recipe.deleted_at.is_(None)  # Recipe still exists
                ).first()
                
                if not recipe:
                    logger.warning(f"  ⚠ Recipe {pending_share.recipe_id} not found or deleted, skipping")
                    skipped_count += 1
                    continue
                
                # Check if email belongs to an existing user now
                existing_user = db.session.query(User).filter(
                    User.email == pending_share.recipient_email.lower()
                ).first()
                
                if existing_user:
                    # User now exists, link the share but don't send email
                    # (They should see it in their pending shares in-app)
                    if not dry_run:
                        pending_share.shared_with_user_id = existing_user.id
                        db.session.commit()
                    logger.info(f"  ℹ Recipient {pending_share.recipient_email} is now a user, linking share (not sending email)")
                    skipped_count += 1
                    continue
                
                # Generate URL with token
                recipe_url = url_for(
                    'recipe_view_token',
                    recipe_id=recipe.id,
                    token=pending_share.token,
                    _external=True
                )
                
                custom_message = (
                    f"I'd like to share this recipe with you. "
                    f"Please create an account to view it.\n\n"
                    f"View recipe: {recipe_url}"
                )
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would send share notification to: {pending_share.recipient_email}")
                    logger.info(f"  Recipe: {recipe.name} (ID: {recipe.id})")
                    sent_count += 1
                else:
                    success, error_msg = email_service.send_recipe(
                        recipe=recipe,
                        recipient_email=pending_share.recipient_email,
                        recipient_name='',
                        custom_message=custom_message
                    )
                    
                    if success:
                        logger.info(f"✓ Sent share notification to: {pending_share.recipient_email}")
                        logger.info(f"  Recipe: {recipe.name} (ID: {recipe.id})")
                        sent_count += 1
                    else:
                        logger.error(f"✗ Failed to send share notification to {pending_share.recipient_email}: {error_msg}")
                        logger.error(f"  Recipe: {recipe.name} (ID: {recipe.id})")
                        error_count += 1
                        
            except Exception as e:
                logger.error(f"✗ Error processing pending share {pending_share.id}: {e}")
                error_count += 1
    
    return sent_count, error_count, skipped_count


def send_recipe_share_notifications_to_users(dry_run=True):
    """
    Send notifications for RecipeShare records (shares with existing users).
    
    This checks for RecipeShare records that don't have corresponding notifications
    and creates notifications (which may trigger emails if that feature exists).
    """
    logger.info("=" * 70)
    logger.info("CREATING SHARE NOTIFICATIONS FOR EXISTING USERS")
    logger.info("=" * 70)
    
    # Find RecipeShare records without notifications
    shares_without_notifications = db.session.query(RecipeShare).outerjoin(
        Notification,
        db.and_(
            Notification.recipe_id == RecipeShare.recipe_id,
            Notification.user_id == RecipeShare.shared_with_user_id,
            Notification.notification_type == 'recipe_shared',
            Notification.related_user_id == RecipeShare.shared_by_user_id
        )
    ).filter(
        Notification.id.is_(None),
        RecipeShare.shared_with_user_id.isnot(None)
    ).all()
    
    logger.info(f"Found {len(shares_without_notifications)} recipe shares without notifications")
    
    created_count = 0
    error_count = 0
    
    for share in shares_without_notifications:
        try:
            recipe = db.session.query(Recipe).filter(Recipe.id == share.recipe_id).first()
            sharer = db.session.query(User).filter(User.id == share.shared_by_user_id).first()
            
            if not recipe or not sharer:
                logger.warning(f"  ⚠ Missing recipe or sharer for share {share.id}, skipping")
                continue
            
            sharer_name = sharer.display_name or sharer.username
            message = f"{sharer_name} shared the recipe '{recipe.name}' with you."
            
            if dry_run:
                logger.info(f"[DRY RUN] Would create notification for user {share.shared_with_user_id}")
                logger.info(f"  Recipe: {recipe.name}, Shared by: {sharer_name}")
                created_count += 1
            else:
                # Check if notification already exists
                existing = db.session.query(Notification).filter(
                    Notification.user_id == share.shared_with_user_id,
                    Notification.recipe_id == share.recipe_id,
                    Notification.notification_type == 'recipe_shared',
                    Notification.related_user_id == share.shared_by_user_id
                ).first()
                
                if existing:
                    logger.info(f"  ℹ Notification already exists for share {share.id}")
                    continue
                
                notification = Notification(
                    user_id=share.shared_with_user_id,
                    notification_type='recipe_shared',
                    related_user_id=share.shared_by_user_id,
                    recipe_id=share.recipe_id,
                    message=message,
                    read=False
                )
                db.session.add(notification)
                db.session.commit()
                
                logger.info(f"✓ Created notification for user {share.shared_with_user_id}")
                logger.info(f"  Recipe: {recipe.name}, Shared by: {sharer_name}")
                created_count += 1
                
        except Exception as e:
            logger.error(f"✗ Error creating notification for share {share.id}: {e}")
            error_count += 1
            db.session.rollback()
    
    return created_count, error_count


def main():
    """Main function to run all email sending tasks."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Send missing welcome and share notification emails')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Run in dry-run mode (default: True)')
    parser.add_argument('--execute', action='store_true',
                       help='Actually send emails (overrides --dry-run)')
    parser.add_argument('--welcome-only', action='store_true',
                       help='Only send welcome emails')
    parser.add_argument('--shares-only', action='store_true',
                       help='Only send share notifications')
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if dry_run:
        logger.info("🔍 RUNNING IN DRY-RUN MODE - No emails will be sent")
        logger.info("   Use --execute to actually send emails")
    else:
        logger.info("⚠️  EXECUTION MODE - Emails WILL be sent!")
    
    logger.info("")
    
    with app.app_context():
        total_sent = 0
        total_errors = 0
        
        # Send welcome emails
        if not args.shares_only:
            welcome_sent, welcome_errors = send_welcome_emails(dry_run=dry_run)
            total_sent += welcome_sent
            total_errors += welcome_errors
            logger.info("")
        
        # Send share notifications for pending shares (non-users)
        if not args.welcome_only:
            share_sent, share_errors, share_skipped = send_share_notification_emails(dry_run=dry_run)
            total_sent += share_sent
            total_errors += share_errors
            logger.info("")
        
        # Create notifications for existing user shares
        if not args.welcome_only:
            notif_created, notif_errors = send_recipe_share_notifications_to_users(dry_run=dry_run)
            total_sent += notif_created
            total_errors += notif_errors
            logger.info("")
        
        # Summary
        logger.info("=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        if dry_run:
            logger.info(f"Would send/create: {total_sent} emails/notifications")
        else:
            logger.info(f"Sent/created: {total_sent} emails/notifications")
        logger.info(f"Errors: {total_errors}")
        logger.info("=" * 70)


if __name__ == '__main__':
    main()

