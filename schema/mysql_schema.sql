-- ============================================================================
-- Recipe Editor - Multi-User MySQL Database Schema
-- ============================================================================
-- Version: 1.0
-- Description: Complete schema for multi-user recipe management with
--              normalized ingredients, meal planning, and user organization
-- Tables: 14 total
-- ============================================================================

-- Create database
CREATE DATABASE IF NOT EXISTS recipe_editor 
    DEFAULT CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE recipe_editor;

-- ============================================================================
-- USER MANAGEMENT (3 tables)
-- ============================================================================

-- Core user accounts
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    bio TEXT,
    avatar_url VARCHAR(500),
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User preferences
CREATE TABLE user_preferences (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    measurement_system ENUM('metric', 'imperial') DEFAULT 'imperial',
    dietary_restrictions JSON,
    allergens JSON,
    email_notifications BOOLEAN DEFAULT TRUE,
    default_visibility ENUM('private', 'public', 'unlisted') DEFAULT 'private',
    theme VARCHAR(20) DEFAULT 'light',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_prefs (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Password reset tokens
CREATE TABLE password_reset_tokens (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_token (token),
    INDEX idx_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- INGREDIENTS (3 tables) - Smart Ingredient System
-- ============================================================================

-- Master ingredient catalog
CREATE TABLE ingredients (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) UNIQUE NOT NULL,
    plural_name VARCHAR(200),
    category VARCHAR(50),
    subcategory VARCHAR(50),
    aliases JSON,
    is_common BOOLEAN DEFAULT FALSE,
    allergen_info JSON,
    nutritional_data JSON,
    default_unit VARCHAR(20),
    storage_tips TEXT,
    substitution_suggestions JSON,
    seasonal_info JSON,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_category (category),
    INDEX idx_common (is_common),
    INDEX idx_usage (usage_count DESC),
    FULLTEXT idx_search (name, plural_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Recipe ingredients with measurements
CREATE TABLE recipe_ingredients (
    id INT PRIMARY KEY AUTO_INCREMENT,
    recipe_id INT NOT NULL,
    ingredient_id INT NOT NULL,
    amount VARCHAR(50),
    unit VARCHAR(50),
    preparation VARCHAR(200),
    is_optional BOOLEAN DEFAULT FALSE,
    notes TEXT,
    sort_order INT DEFAULT 0,
    ingredient_group VARCHAR(100),
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE RESTRICT,
    INDEX idx_recipe_order (recipe_id, sort_order),
    INDEX idx_ingredient (ingredient_id),
    INDEX idx_recipe (recipe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User ingredient substitutions
CREATE TABLE user_ingredient_substitutions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    original_ingredient_id INT NOT NULL,
    substitute_ingredient_id INT NOT NULL,
    reason VARCHAR(200),
    auto_apply BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (original_ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
    FOREIGN KEY (substitute_ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
    UNIQUE KEY unique_substitution (user_id, original_ingredient_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- RECIPES (3 tables)
-- ============================================================================

-- Main recipes table
CREATE TABLE recipes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    instructions TEXT NOT NULL,
    notes TEXT,
    prep_time INT,
    cook_time INT,
    total_time INT GENERATED ALWAYS AS (IFNULL(prep_time, 0) + IFNULL(cook_time, 0)) STORED,
    servings VARCHAR(50),
    difficulty ENUM('easy', 'medium', 'hard'),
    visibility ENUM('private', 'public', 'unlisted') DEFAULT 'private',
    slug VARCHAR(250) UNIQUE,
    meta_description VARCHAR(300),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    published_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_slug (slug),
    INDEX idx_visibility (visibility),
    INDEX idx_published (visibility, published_at DESC),
    INDEX idx_created (created_at DESC),
    FULLTEXT idx_search (name, description, instructions, notes)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Recipe sources
CREATE TABLE recipe_sources (
    id INT PRIMARY KEY AUTO_INCREMENT,
    recipe_id INT NOT NULL,
    source_name VARCHAR(200),
    source_url TEXT,
    author VARCHAR(200),
    issue VARCHAR(100),
    imported_from ENUM('manual', 'url', 'pdf', 'text_file', 'api') DEFAULT 'manual',
    imported_at TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    UNIQUE KEY unique_recipe_source (recipe_id),
    INDEX idx_author (author)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Recipe photos
CREATE TABLE recipe_photos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    recipe_id INT NOT NULL,
    photo_url VARCHAR(500) NOT NULL,
    photo_type ENUM('main', 'step', 'result', 'gallery') DEFAULT 'gallery',
    caption TEXT,
    step_number INT,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    INDEX idx_recipe_type (recipe_id, photo_type),
    INDEX idx_recipe_order (recipe_id, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TAGS (2 tables)
-- ============================================================================

CREATE TABLE tags (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    tag_type ENUM('cuisine', 'diet', 'meal_type', 'method', 'occasion', 'season', 'other') DEFAULT 'other',
    icon VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_slug (slug),
    INDEX idx_type (tag_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE recipe_tags (
    recipe_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (recipe_id, tag_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    INDEX idx_tag_recipe (tag_id, recipe_id),
    INDEX idx_recipe (recipe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- USER INTERACTIONS (3 tables)
-- ============================================================================

-- User favorites
CREATE TABLE recipe_favorites (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    recipe_id INT NOT NULL,
    personal_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    UNIQUE KEY unique_favorite (user_id, recipe_id),
    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_recipe (recipe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User ratings & reviews
CREATE TABLE recipe_ratings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    recipe_id INT NOT NULL,
    rating DECIMAL(2,1) NOT NULL CHECK (rating >= 0 AND rating <= 5),
    review TEXT,
    modifications TEXT,
    would_make_again BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    UNIQUE KEY unique_rating (user_id, recipe_id),
    INDEX idx_recipe_rating (recipe_id, rating DESC),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Collections/Cookbooks
CREATE TABLE collections (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    cover_photo_url VARCHAR(500),
    visibility ENUM('private', 'public') DEFAULT 'private',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_visibility (visibility)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE collection_recipes (
    collection_id INT NOT NULL,
    recipe_id INT NOT NULL,
    sort_order INT DEFAULT 0,
    personal_notes TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection_id, recipe_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    INDEX idx_collection_order (collection_id, sort_order),
    INDEX idx_recipe (recipe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- MEAL PLANNING (2 tables)
-- ============================================================================

CREATE TABLE meal_plans (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    name VARCHAR(200),
    start_date DATE,
    end_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_date (user_id, start_date DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE meal_plan_recipes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    meal_plan_id INT NOT NULL,
    recipe_id INT NOT NULL,
    planned_date DATE NOT NULL,
    meal_type ENUM('breakfast', 'lunch', 'dinner', 'snack', 'dessert', 'other'),
    servings_planned INT,
    notes TEXT,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    FOREIGN KEY (meal_plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    INDEX idx_plan_date (meal_plan_id, planned_date),
    INDEX idx_recipe (recipe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- STATISTICS (2 tables)
-- ============================================================================

-- Recipe statistics (cached/denormalized)
CREATE TABLE recipe_stats (
    recipe_id INT PRIMARY KEY,
    view_count INT DEFAULT 0,
    unique_view_count INT DEFAULT 0,
    favorite_count INT DEFAULT 0,
    rating_count INT DEFAULT 0,
    average_rating DECIMAL(3,2) DEFAULT 0,
    review_count INT DEFAULT 0,
    email_share_count INT DEFAULT 0,
    print_count INT DEFAULT 0,
    last_viewed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    INDEX idx_popular (favorite_count DESC, average_rating DESC),
    INDEX idx_trending (view_count DESC, last_viewed_at DESC),
    INDEX idx_rating (average_rating DESC, rating_count DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User statistics (cached)
CREATE TABLE user_stats (
    user_id INT PRIMARY KEY,
    recipe_count INT DEFAULT 0,
    public_recipe_count INT DEFAULT 0,
    private_recipe_count INT DEFAULT 0,
    collection_count INT DEFAULT 0,
    total_recipe_views INT DEFAULT 0,
    total_recipe_favorites INT DEFAULT 0,
    average_recipe_rating DECIMAL(3,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- EMAIL SHARING TRACKING (1 table)
-- ============================================================================

-- Track recipe emails sent (for existing email feature)
CREATE TABLE recipe_email_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    recipe_id INT NOT NULL,
    sent_by_user_id INT,
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(100),
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (sent_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_recipe (recipe_id),
    INDEX idx_user (sent_by_user_id),
    INDEX idx_sent (sent_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TRIGGERS FOR STATISTICS (Auto-update cached counts)
-- ============================================================================

-- Update recipe_stats when favorite added/removed
DELIMITER $$

CREATE TRIGGER after_favorite_insert
AFTER INSERT ON recipe_favorites
FOR EACH ROW
BEGIN
    INSERT INTO recipe_stats (recipe_id, favorite_count)
    VALUES (NEW.recipe_id, 1)
    ON DUPLICATE KEY UPDATE 
        favorite_count = favorite_count + 1;
END$$

CREATE TRIGGER after_favorite_delete
AFTER DELETE ON recipe_favorites
FOR EACH ROW
BEGIN
    UPDATE recipe_stats
    SET favorite_count = GREATEST(0, favorite_count - 1)
    WHERE recipe_id = OLD.recipe_id;
END$$

-- Update recipe_stats when rating added/updated/removed
CREATE TRIGGER after_rating_insert
AFTER INSERT ON recipe_ratings
FOR EACH ROW
BEGIN
    INSERT INTO recipe_stats (recipe_id, rating_count, average_rating, review_count)
    VALUES (
        NEW.recipe_id,
        1,
        NEW.rating,
        IF(NEW.review IS NOT NULL AND NEW.review != '', 1, 0)
    )
    ON DUPLICATE KEY UPDATE
        rating_count = rating_count + 1,
        review_count = review_count + IF(NEW.review IS NOT NULL AND NEW.review != '', 1, 0),
        average_rating = (
            SELECT AVG(rating)
            FROM recipe_ratings
            WHERE recipe_id = NEW.recipe_id
        );
END$$

CREATE TRIGGER after_rating_update
AFTER UPDATE ON recipe_ratings
FOR EACH ROW
BEGIN
    UPDATE recipe_stats
    SET 
        average_rating = (
            SELECT AVG(rating)
            FROM recipe_ratings
            WHERE recipe_id = NEW.recipe_id
        ),
        review_count = (
            SELECT COUNT(*)
            FROM recipe_ratings
            WHERE recipe_id = NEW.recipe_id
            AND review IS NOT NULL AND review != ''
        )
    WHERE recipe_id = NEW.recipe_id;
END$$

CREATE TRIGGER after_rating_delete
AFTER DELETE ON recipe_ratings
FOR EACH ROW
BEGIN
    UPDATE recipe_stats
    SET 
        rating_count = GREATEST(0, rating_count - 1),
        review_count = GREATEST(0, review_count - IF(OLD.review IS NOT NULL AND OLD.review != '', 1, 0)),
        average_rating = IFNULL((
            SELECT AVG(rating)
            FROM recipe_ratings
            WHERE recipe_id = OLD.recipe_id
        ), 0)
    WHERE recipe_id = OLD.recipe_id;
END$$

-- Update user_stats when recipe created/deleted
CREATE TRIGGER after_recipe_insert
AFTER INSERT ON recipes
FOR EACH ROW
BEGIN
    INSERT INTO user_stats (user_id, recipe_count, public_recipe_count, private_recipe_count)
    VALUES (
        NEW.user_id,
        1,
        IF(NEW.visibility = 'public', 1, 0),
        IF(NEW.visibility = 'private', 1, 0)
    )
    ON DUPLICATE KEY UPDATE
        recipe_count = recipe_count + 1,
        public_recipe_count = public_recipe_count + IF(NEW.visibility = 'public', 1, 0),
        private_recipe_count = private_recipe_count + IF(NEW.visibility = 'private', 1, 0);
    
    -- Initialize recipe_stats
    INSERT INTO recipe_stats (recipe_id) VALUES (NEW.id);
END$$

CREATE TRIGGER after_recipe_delete
AFTER DELETE ON recipes
FOR EACH ROW
BEGIN
    UPDATE user_stats
    SET 
        recipe_count = GREATEST(0, recipe_count - 1),
        public_recipe_count = GREATEST(0, public_recipe_count - IF(OLD.visibility = 'public', 1, 0)),
        private_recipe_count = GREATEST(0, private_recipe_count - IF(OLD.visibility = 'private', 1, 0))
    WHERE user_id = OLD.user_id;
END$$

-- Update ingredient usage_count
CREATE TRIGGER after_recipe_ingredient_insert
AFTER INSERT ON recipe_ingredients
FOR EACH ROW
BEGIN
    UPDATE ingredients
    SET usage_count = usage_count + 1
    WHERE id = NEW.ingredient_id;
END$$

CREATE TRIGGER after_recipe_ingredient_delete
AFTER DELETE ON recipe_ingredients
FOR EACH ROW
BEGIN
    UPDATE ingredients
    SET usage_count = GREATEST(0, usage_count - 1)
    WHERE id = OLD.ingredient_id;
END$$

DELIMITER ;

-- ============================================================================
-- INITIAL DATA - Common Ingredients
-- ============================================================================

-- Insert common ingredients to get started
INSERT INTO ingredients (name, plural_name, category, is_common, default_unit) VALUES
-- Dairy
('milk', 'milk', 'dairy', TRUE, 'cups'),
('butter', 'butter', 'dairy', TRUE, 'tablespoons'),
('egg', 'eggs', 'dairy', TRUE, 'whole'),
('cheese', 'cheese', 'dairy', TRUE, 'cups'),
('cream', 'cream', 'dairy', TRUE, 'cups'),
('yogurt', 'yogurt', 'dairy', TRUE, 'cups'),

-- Grains & Flour
('all-purpose flour', 'all-purpose flour', 'grain', TRUE, 'cups'),
('bread', 'bread', 'grain', TRUE, 'slices'),
('rice', 'rice', 'grain', TRUE, 'cups'),
('pasta', 'pasta', 'grain', TRUE, 'oz'),
('oats', 'oats', 'grain', TRUE, 'cups'),

-- Proteins
('chicken breast', 'chicken breasts', 'meat', TRUE, 'lbs'),
('ground beef', 'ground beef', 'meat', TRUE, 'lbs'),
('bacon', 'bacon', 'meat', TRUE, 'slices'),
('salmon', 'salmon', 'seafood', TRUE, 'lbs'),
('shrimp', 'shrimp', 'seafood', TRUE, 'lbs'),

-- Vegetables
('onion', 'onions', 'vegetable', TRUE, 'whole'),
('garlic', 'garlic', 'vegetable', TRUE, 'cloves'),
('tomato', 'tomatoes', 'vegetable', TRUE, 'whole'),
('potato', 'potatoes', 'vegetable', TRUE, 'whole'),
('carrot', 'carrots', 'vegetable', TRUE, 'whole'),
('bell pepper', 'bell peppers', 'vegetable', TRUE, 'whole'),
('spinach', 'spinach', 'vegetable', TRUE, 'cups'),
('broccoli', 'broccoli', 'vegetable', TRUE, 'cups'),

-- Spices & Seasonings
('salt', 'salt', 'spice', TRUE, 'teaspoons'),
('black pepper', 'black pepper', 'spice', TRUE, 'teaspoons'),
('olive oil', 'olive oil', 'oil', TRUE, 'tablespoons'),
('vegetable oil', 'vegetable oil', 'oil', TRUE, 'tablespoons'),
('sugar', 'sugar', 'sweetener', TRUE, 'cups'),
('brown sugar', 'brown sugar', 'sweetener', TRUE, 'cups'),

-- Baking
('baking powder', 'baking powder', 'leavening', TRUE, 'teaspoons'),
('baking soda', 'baking soda', 'leavening', TRUE, 'teaspoons'),
('vanilla extract', 'vanilla extract', 'flavoring', TRUE, 'teaspoons'),
('chocolate chips', 'chocolate chips', 'baking', TRUE, 'cups');

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Complete recipe view with all related data
CREATE VIEW recipe_detail_view AS
SELECT 
    r.*,
    u.username as owner_username,
    u.display_name as owner_display_name,
    rs.source_name,
    rs.source_url,
    rs.author as source_author,
    rs.issue as source_issue,
    rs.imported_from,
    stats.view_count,
    stats.favorite_count,
    stats.average_rating,
    stats.rating_count,
    (SELECT GROUP_CONCAT(t.name ORDER BY t.name SEPARATOR ',')
     FROM recipe_tags rt
     JOIN tags t ON rt.tag_id = t.id
     WHERE rt.recipe_id = r.id) as tags
FROM recipes r
JOIN users u ON r.user_id = u.id
LEFT JOIN recipe_sources rs ON r.id = rs.recipe_id
LEFT JOIN recipe_stats stats ON r.id = stats.recipe_id;

-- User's favorite recipes with details
CREATE VIEW user_favorites_view AS
SELECT 
    rf.user_id,
    r.*,
    rf.personal_notes as favorite_notes,
    rf.created_at as favorited_at,
    u.username as recipe_owner_username
FROM recipe_favorites rf
JOIN recipes r ON rf.recipe_id = r.id
JOIN users u ON r.user_id = u.id;

-- Popular ingredients
CREATE VIEW popular_ingredients_view AS
SELECT 
    i.id,
    i.name,
    i.category,
    i.usage_count,
    COUNT(DISTINCT ri.recipe_id) as actual_recipe_count
FROM ingredients i
LEFT JOIN recipe_ingredients ri ON i.id = ri.ingredient_id
GROUP BY i.id
ORDER BY i.usage_count DESC;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

