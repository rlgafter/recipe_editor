"""
Recipe Editor - Main Flask Application
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import logging
from logging.handlers import RotatingFileHandler
import os
import config
from models import Recipe, Ingredient
from storage import storage
from email_service import email_service

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
        return render_template('recipe_form.html', recipe=None, all_tags=all_tags, new_tags=[])
    
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
            return render_template('recipe_form.html', recipe=recipe, all_tags=all_tags, new_tags=new_tags), 400
        
        # Save recipe
        saved_recipe = storage.save_recipe(recipe)
        flash(f'Recipe "{saved_recipe.name}" created successfully!', 'success')
        app.logger.info(f"Created new recipe {saved_recipe.id}: {saved_recipe.name}")
        
        return redirect(url_for('recipe_view', recipe_id=saved_recipe.id))
    
    except Exception as e:
        app.logger.error(f"Error creating recipe: {str(e)}")
        flash('Error creating recipe. Please try again.', 'error')
        all_tags = storage.get_all_tags()
        return render_template('recipe_form.html', recipe=None, all_tags=all_tags, new_tags=[]), 500


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
        return render_template('recipe_form.html', recipe=recipe, all_tags=all_tags, new_tags=new_tags)
    
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
            return render_template('recipe_form.html', recipe=updated_recipe, all_tags=all_tags, new_tags=new_tags), 400
        
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
        return render_template('recipe_form.html', recipe=recipe, all_tags=all_tags, new_tags=new_tags), 500


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
    
    if not email_service.is_configured():
        flash('Email service is not configured. Please set SMTP environment variables.', 'error')
        return redirect(url_for('recipe_view', recipe_id=recipe_id))
    
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
        success, error_msg = email_service.send_recipe(
            recipe,
            recipient_email,
            recipient_name,
            custom_message
        )
        
        if success:
            flash(f'Recipe sent successfully to {recipient_email}!', 'success')
            app.logger.info(f"Emailed recipe {recipe_id} to {recipient_email}")
            return redirect(url_for('recipe_view', recipe_id=recipe_id))
        else:
            flash(f'Error sending email: {error_msg}', 'error')
            return render_template('recipe_email.html', recipe=recipe), 500
    
    except Exception as e:
        app.logger.error(f"Error emailing recipe {recipe_id}: {str(e)}")
        flash('Error sending email. Please try again.', 'error')
        return render_template('recipe_email.html', recipe=recipe), 500


# ============================================================================
# Routes - Tag Management
# ============================================================================

@app.route('/tags', methods=['GET', 'POST'])
def tag_manager():
    """Manage tags (list, create, edit, delete)."""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            tag_name = request.form.get('tag_name', '').strip().lower()
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
            old_name = request.form.get('old_name', '').strip().lower()
            new_name = request.form.get('new_name', '').strip().lower()
            
            success, error_msg = storage.update_tag_name(old_name, new_name)
            if success:
                flash(f'Tag renamed from "{old_name}" to "{new_name}"', 'success')
            else:
                flash(error_msg, 'error')
        
        elif action == 'delete':
            tag_name = request.form.get('tag_name', '').strip().lower()
            
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
# Helper Functions
# ============================================================================

def _parse_recipe_form(form_data, recipe_id=None):
    """Parse recipe data from form submission."""
    # Get basic fields
    name = form_data.get('name', '').strip()
    instructions = form_data.get('instructions', '').strip()
    notes = form_data.get('notes', '').strip()
    
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
        recipe_id=recipe_id
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

