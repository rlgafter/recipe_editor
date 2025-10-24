"""
Recipe Editor - Main Flask Application
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import config
from models import Recipe, Ingredient
from storage import storage
from email_service import email_service
from gemini_service import gemini_service

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Configure logging
if not os.path.exists(config.LOGS_DIR):
    os.makedirs(config.LOGS_DIR)

file_handler = RotatingFileHandler(
    config.LOG_FILE,
    maxBytes=1024 * 1024,  # 1MB
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
console_handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

app.logger.info("Recipe Editor application starting")


# ============================================================================
# Routes - Recipe Management
# ============================================================================

@app.route('/')
@app.route('/recipes')
def recipe_list():
    """Display list of all recipes with optional tag filtering."""
    # Get filter parameters
    selected_tags = request.args.getlist('tags')
    match_all = request.args.get('match_all') == 'true'
    
    # Get all tags for the filter interface
    all_tags = storage.get_all_tags()
    
    # Get recipes (filtered or all)
    if selected_tags:
        recipes = storage.filter_recipes_by_tags(selected_tags, match_all)
        app.logger.info(f"Filtered recipes by tags: {selected_tags} (match_all={match_all})")
    else:
        recipes = storage.get_all_recipes()
    
    # Sort recipes by name
    recipes.sort(key=lambda r: r.name.lower())
    
    return render_template(
        'recipe_list.html',
        recipes=recipes,
        all_tags=all_tags,
        selected_tags=selected_tags,
        match_all=match_all
    )


@app.route('/recipe/<recipe_id>')
def recipe_view(recipe_id):
    """Display a single recipe."""
    recipe = storage.get_recipe(recipe_id)
    
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    app.logger.info(f"Viewing recipe {recipe_id}: {recipe.name}")
    
    # Check if email is configured
    email_configured = email_service.is_configured()
    
    return render_template(
        'recipe_view.html',
        recipe=recipe,
        email_configured=email_configured
    )


@app.route('/recipe/new', methods=['GET', 'POST'])
def recipe_new():
    """Create a new recipe."""
    if request.method == 'GET':
        # Get all tags for selection
        all_tags = storage.get_all_tags()
        # Check if Gemini is configured
        gemini_configured = gemini_service.is_configured()
        return render_template('recipe_form.html', recipe=None, all_tags=all_tags, new_tags=[], gemini_configured=gemini_configured)
    
    # POST - Create new recipe
    try:
        recipe = _parse_recipe_form(request.form)
        
        # Validate recipe
        is_valid, errors = recipe.validate()
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            all_tags = storage.get_all_tags()
            new_tags = [tag for tag in recipe.tags if tag not in all_tags] if recipe.tags else []
            gemini_configured = gemini_service.is_configured()
            return render_template('recipe_form.html', recipe=recipe, all_tags=all_tags, new_tags=new_tags, gemini_configured=gemini_configured), 400
        
        # Save recipe
        saved_recipe = storage.save_recipe(recipe)
        flash(f'Recipe "{saved_recipe.name}" created successfully!', 'success')
        app.logger.info(f"Created new recipe {saved_recipe.id}: {saved_recipe.name}")
        
        return redirect(url_for('recipe_view', recipe_id=saved_recipe.id))
    
    except Exception as e:
        app.logger.error(f"Error creating recipe: {str(e)}")
        flash('Error creating recipe. Please try again.', 'error')
        all_tags = storage.get_all_tags()
        gemini_configured = gemini_service.is_configured()
        return render_template('recipe_form.html', recipe=None, all_tags=all_tags, new_tags=[], gemini_configured=gemini_configured), 500


@app.route('/recipe/<recipe_id>/edit', methods=['GET', 'POST'])
def recipe_edit(recipe_id):
    """Edit an existing recipe."""
    recipe = storage.get_recipe(recipe_id)
    
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    if request.method == 'GET':
        all_tags = storage.get_all_tags()
        # Calculate tags that are not in the existing tags list (new tags)
        new_tags = [tag for tag in recipe.tags if tag not in all_tags]
        gemini_configured = gemini_service.is_configured()
        return render_template('recipe_form.html', recipe=recipe, all_tags=all_tags, new_tags=new_tags, gemini_configured=gemini_configured)
    
    # POST - Update recipe
    try:
        updated_recipe = _parse_recipe_form(request.form, recipe_id=recipe_id)
        
        # Preserve creation timestamp
        updated_recipe.created_at = recipe.created_at
        updated_recipe.update_timestamp()
        
        # Validate recipe
        is_valid, errors = updated_recipe.validate()
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            all_tags = storage.get_all_tags()
            new_tags = [tag for tag in updated_recipe.tags if tag not in all_tags] if updated_recipe.tags else []
            gemini_configured = gemini_service.is_configured()
            return render_template('recipe_form.html', recipe=updated_recipe, all_tags=all_tags, new_tags=new_tags, gemini_configured=gemini_configured), 400
        
        # Save recipe
        storage.save_recipe(updated_recipe)
        flash(f'Recipe "{updated_recipe.name}" updated successfully!', 'success')
        app.logger.info(f"Updated recipe {recipe_id}: {updated_recipe.name}")
        
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    except Exception as e:
        app.logger.error(f"Error updating recipe {recipe_id}: {str(e)}")
        flash('Error updating recipe. Please try again.', 'error')
        all_tags = storage.get_all_tags()
        new_tags = [tag for tag in recipe.tags if tag not in all_tags] if recipe.tags else []
        gemini_configured = gemini_service.is_configured()
        return render_template('recipe_form.html', recipe=recipe, all_tags=all_tags, new_tags=new_tags, gemini_configured=gemini_configured), 500


@app.route('/recipe/<recipe_id>/delete', methods=['POST'])
def recipe_delete(recipe_id):
    """Delete a recipe."""
    recipe = storage.get_recipe(recipe_id)
    
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    try:
        recipe_name = recipe.name
        if storage.delete_recipe(recipe_id):
            flash(f'Recipe "{recipe_name}" deleted successfully', 'success')
            app.logger.info(f"Deleted recipe {recipe_id}: {recipe_name}")
        else:
            flash('Error deleting recipe', 'error')
    except Exception as e:
        app.logger.error(f"Error deleting recipe {recipe_id}: {str(e)}")
        flash('Error deleting recipe', 'error')
    
    return redirect(url_for('recipe_list'))


# ============================================================================
# Routes - Email
# ============================================================================

@app.route('/recipe/<recipe_id>/email', methods=['GET', 'POST'])
def recipe_email(recipe_id):
    """Send recipe via email."""
    recipe = storage.get_recipe(recipe_id)
    
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    # For testing purposes, allow email page even if not configured
    # if not email_service.is_configured():
    #     flash('Email service is not configured. Please set SMTP environment variables.', 'error')
    #     return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
    if request.method == 'GET':
        return render_template('recipe_email.html', recipe=recipe)
    
    # POST - Send email
    recipient_email = request.form.get('recipient_email', '').strip()
    recipient_name = request.form.get('recipient_name', '').strip()
    custom_message = request.form.get('message', '').strip()
    
    if not recipient_email:
        flash('Recipient email is required', 'error')
        return render_template('recipe_email.html', recipe=recipe), 400
    
    try:
        # Check if email service is configured
        if not email_service.is_configured():
            # For testing - simulate successful email sending
            app.logger.info(f"TEST MODE: Would email recipe {recipe_id} to {recipient_email}")
            return jsonify({
                'success': True,
                'message': 'Email sent successfully! (TEST MODE)',
                'recipient_name': recipient_name,
                'recipient_email': recipient_email,
                'custom_message': custom_message,
                'recipe_name': recipe.name
            })
        
        success, error_msg = email_service.send_recipe(
            recipe,
            recipient_email,
            recipient_name,
            custom_message
        )
        
        if success:
            app.logger.info(f"Emailed recipe {recipe_id} to {recipient_email}")
            
            # Return JSON response for AJAX handling with detailed popup
            return jsonify({
                'success': True,
                'message': 'Email sent successfully!',
                'recipient_name': recipient_name,
                'recipient_email': recipient_email,
                'custom_message': custom_message,
                'recipe_name': recipe.name
            })
        else:
            # Return JSON response for AJAX handling with error popup
            return jsonify({
                'success': False,
                'error': error_msg,
                'recipient_email': recipient_email
            }), 500
    
    except Exception as e:
        app.logger.error(f"Error emailing recipe {recipe_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error sending email: {str(e)}',
            'recipient_email': recipient_email
        }), 500


# ============================================================================
# Routes - Tag Management
# ============================================================================

@app.route('/tags', methods=['GET', 'POST'])
def tag_manager():
    """Manage tags (list, create, edit, delete)."""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            tag_name = request.form.get('tag_name', '').strip().upper()
            if not tag_name:
                flash('Tag name is required', 'error')
            else:
                existing_tags = storage.get_all_tags()
                if tag_name in existing_tags:
                    flash(f'Tag "{tag_name}" already exists', 'error')
                else:
                    # Tag will be created automatically when used in a recipe
                    # For now, just show success message
                    flash(f'Tag "{tag_name}" will be available for recipes', 'success')
                    app.logger.info(f"Tag '{tag_name}' registered")
        
        elif action == 'edit':
            old_name = request.form.get('old_name', '').strip().upper()
            new_name = request.form.get('new_name', '').strip().upper()
            
            success, error_msg = storage.update_tag_name(old_name, new_name)
            if success:
                flash(f'Tag renamed from "{old_name}" to "{new_name}"', 'success')
            else:
                flash(error_msg, 'error')
        
        elif action == 'delete':
            tag_name = request.form.get('tag_name', '').strip().upper()
            
            success, error_msg = storage.delete_tag(tag_name)
            if success:
                flash(f'Tag "{tag_name}" deleted', 'success')
            else:
                flash(error_msg, 'error')
    
    # Get all tags
    all_tags = storage.get_all_tags()
    
    # Sort by name
    sorted_tags = sorted(all_tags.items(), key=lambda x: x[0])
    
    return render_template('tag_manager.html', tags=sorted_tags)


# ============================================================================
# Routes - Recipe Import
# ============================================================================

@app.route('/api/recipe/import/url', methods=['POST'])
def import_recipe_from_url():
    """Import recipe from a URL using Gemini AI."""
    if not gemini_service.is_configured():
        return jsonify({
            'success': False,
            'error': 'Gemini API is not configured. Please set GOOGLE_GEMINI_API_KEY environment variable.'
        }), 500
    
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        # Extract recipe using Gemini
        success, recipe_data, error_msg = gemini_service.extract_from_url(url)
        
        if success and recipe_data:
            app.logger.info(f"Successfully imported recipe from URL: {url}")
            return jsonify({'success': True, 'recipe': recipe_data})
        else:
            app.logger.error(f"Failed to import recipe from URL: {error_msg}")
            return jsonify({'success': False, 'error': error_msg or 'Could not extract recipe from URL'}), 400
    
    except Exception as e:
        app.logger.error(f"Error importing recipe from URL: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recipe/import/file', methods=['POST'])
def import_recipe_from_file():
    """Import recipe from a file (text or PDF) using Gemini AI."""
    if not gemini_service.is_configured():
        return jsonify({
            'success': False,
            'error': 'Gemini API is not configured. Please set GOOGLE_GEMINI_API_KEY environment variable.'
        }), 500
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        filename = file.filename
        file_content = file.read()
        
        # Determine file type and extract accordingly
        if filename.lower().endswith('.pdf'):
            success, recipe_data, error_msg = gemini_service.extract_from_pdf(file_content, filename)
        elif filename.lower().endswith(('.txt', '.text')):
            text_content = file_content.decode('utf-8', errors='ignore')
            success, recipe_data, error_msg = gemini_service.extract_from_text(text_content, filename)
        else:
            # Try as text file by default
            try:
                text_content = file_content.decode('utf-8', errors='ignore')
                success, recipe_data, error_msg = gemini_service.extract_from_text(text_content, filename)
            except Exception as e:
                return jsonify({'success': False, 'error': f'Unsupported file type: {filename}'}), 400
        
        if success and recipe_data:
            app.logger.info(f"Successfully imported recipe from file: {filename}")
            return jsonify({'success': True, 'recipe': recipe_data})
        else:
            app.logger.error(f"Failed to import recipe from file: {error_msg}")
            return jsonify({'success': False, 'error': error_msg or 'Could not extract recipe from file'}), 400
    
    except Exception as e:
        app.logger.error(f"Error importing recipe from file: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Helper Functions
# ============================================================================

def _convert_unicode_fractions(amount: str) -> str:
    """
    Convert unicode fraction characters to ASCII equivalents.
    Also handles common variations and spacing issues.
    
    Examples:
        '½' -> '1/2'
        '¼' -> '1/4'
        '¾' -> '3/4'
        '1½' -> '1 1/2'
        '2¼' -> '2 1/4'
        '1 1 /2' -> '1 1/2'
    """
    if not amount:
        return amount
    
    original_amount = amount
    
    # Map of unicode fractions to ASCII
    unicode_fractions = {
        '¼': '1/4',
        '½': '1/2',
        '¾': '3/4',
        '⅐': '1/7',
        '⅑': '1/9',
        '⅒': '1/10',
        '⅓': '1/3',
        '⅔': '2/3',
        '⅕': '1/5',
        '⅖': '2/5',
        '⅗': '3/5',
        '⅘': '4/5',
        '⅙': '1/6',
        '⅚': '5/6',
        '⅛': '1/8',
        '⅜': '3/8',
        '⅝': '5/8',
        '⅞': '7/8',
    }
    
    # First, detect and convert mixed unicode fractions (e.g., '1½' -> '1 1/2')
    for unicode_char, ascii_fraction in unicode_fractions.items():
        if unicode_char in amount:
            # Check if there's a digit before the unicode fraction
            pattern = r'(\d+)' + re.escape(unicode_char)
            match = re.search(pattern, amount)
            if match:
                # Mixed fraction: digit + unicode fraction
                whole_number = match.group(1)
                amount = amount.replace(match.group(0), f"{whole_number} {ascii_fraction}")
                app.logger.debug(f"[UNICODE DEBUG] Converted mixed fraction: '{original_amount}' -> '{amount}'")
            else:
                # Simple unicode fraction
                amount = amount.replace(unicode_char, ascii_fraction)
                app.logger.debug(f"[UNICODE DEBUG] Converted simple fraction: '{original_amount}' -> '{amount}'")
    
    # Fix spacing issues in fractions (e.g., '1 1 /2' -> '1 1/2')
    # Pattern: digit + space(s) + digit + space(s) + / + digit
    amount = re.sub(r'(\d+)\s+(\d+)\s*/\s*(\d+)', r'\1 \2/\3', amount)
    
    # Fix spacing issues in simple fractions (e.g., '1 /2' -> '1/2')
    amount = re.sub(r'(\d+)\s*/\s*(\d+)', r'\1/\2', amount)
    
    if amount != original_amount:
        app.logger.info(f"[AMOUNT CONVERSION] '{original_amount}' -> '{amount}'")
    
    return amount.strip()


def _parse_recipe_form(form_data, recipe_id=None):
    """Parse recipe data from form submission."""
    # Get basic fields
    name = form_data.get('name', '').strip()
    instructions = form_data.get('instructions', '').strip()
    notes = form_data.get('notes', '').strip()
    
    # Parse source information
    source = {
        'name': form_data.get('source_name', '').strip(),
        'url': form_data.get('source_url', '').strip(),
        'author': form_data.get('source_author', '').strip(),
        'issue': form_data.get('source_issue', '').strip()
    }
    
    # Parse ingredients
    ingredients = []
    ingredient_count = 0
    
    # Count how many ingredient entries there are
    while f'ingredient_description_{ingredient_count}' in form_data:
        description = form_data.get(f'ingredient_description_{ingredient_count}', '').strip()
        
        # Only add ingredient if it has a description
        if description:
            amount = form_data.get(f'ingredient_amount_{ingredient_count}', '').strip()
            unit = form_data.get(f'ingredient_unit_{ingredient_count}', '').strip()
            
            # Convert unicode fractions to ASCII (with debug logging)
            if amount:
                app.logger.debug(f"[INGREDIENT {ingredient_count}] Raw amount: '{amount}'")
                amount = _convert_unicode_fractions(amount)
                app.logger.debug(f"[INGREDIENT {ingredient_count}] Converted amount: '{amount}'")
            
            ingredient = Ingredient(amount=amount, unit=unit, description=description)
            ingredients.append(ingredient)
        
        ingredient_count += 1
    
    # Parse tags
    tags = []
    tag_input = form_data.get('tags', '').strip()
    if tag_input:
        # Tags can be comma-separated
        tags = [tag.strip() for tag in tag_input.split(',') if tag.strip()]
    
    # Also check for individual tag checkboxes (for when we have existing tags)
    for key in form_data:
        if key.startswith('tag_'):
            tag_name = key[4:]  # Remove 'tag_' prefix
            if tag_name and tag_name not in tags:
                tags.append(tag_name)
    
    # Create recipe
    recipe = Recipe(
        name=name,
        ingredients=ingredients,
        instructions=instructions,
        notes=notes,
        tags=tags,
        recipe_id=recipe_id,
        source=source
    )
    
    return recipe


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    app.logger.error(f"Internal server error: {str(e)}")
    return render_template('500.html'), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    app.logger.info(f"Starting Recipe Editor on {config.HOST}:{config.PORT}")
    app.logger.info(f"Debug mode: {config.DEBUG}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)

