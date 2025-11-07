# Recipe Editor - Database Schema Diagram

## Entity Relationship Diagram (Mermaid Format)

This diagram can be rendered in GitHub, GitLab, or using Mermaid Live Editor: https://mermaid.live/

```mermaid
erDiagram
    %% USER MANAGEMENT CLUSTER
    users ||--o{ user_preferences : "has"
    users ||--o{ password_reset_tokens : "has"
    users ||--o{ user_stats : "has"
    
    %% USER TO RECIPES
    users ||--o{ recipes : "owns"
    users ||--o{ recipe_favorites : "favorites"
    users ||--o{ recipe_ratings : "rates"
    users ||--o{ collections : "creates"
    users ||--o{ meal_plans : "plans"
    users ||--o{ user_ingredient_substitutions : "customizes"
    users ||--o{ recipe_email_log : "sends"
    users ||--o{ tags : "owns (personal tags)"
    
    %% RECIPES CLUSTER
    recipes ||--o{ recipe_ingredients : "contains"
    recipes ||--o| recipe_sources : "has"
    recipes ||--o{ recipe_photos : "has"
    recipes ||--o| recipe_stats : "has"
    recipes ||--o{ recipe_favorites : "favorited by"
    recipes ||--o{ recipe_ratings : "rated by"
    recipes ||--o{ collection_recipes : "in"
    recipes ||--o{ meal_plan_recipes : "scheduled in"
    recipes ||--o{ recipe_email_log : "emailed"
    recipes }o--o{ tags : "tagged with"
    
    %% INGREDIENTS CLUSTER
    ingredients ||--o{ recipe_ingredients : "used in"
    ingredients ||--o{ user_ingredient_substitutions : "original"
    ingredients ||--o{ user_ingredient_substitutions : "substitute"
    
    %% TAGS
    tags }o--o{ recipes : "categorizes"
    
    %% COLLECTIONS
    collections ||--o{ collection_recipes : "contains"
    collection_recipes }o--|| recipes : "includes"
    
    %% MEAL PLANNING
    meal_plans ||--o{ meal_plan_recipes : "includes"
    meal_plan_recipes }o--|| recipes : "uses"
    
    %% TABLE DEFINITIONS
    
    users {
        int id PK
        string username UK
        string email UK
        string password_hash
        string display_name
        string avatar_url
        boolean email_verified
        boolean is_active
        boolean is_admin
        boolean can_publish_public
        timestamp created_at
        timestamp updated_at
        timestamp last_login
        string password_setup_token
        timestamp password_setup_expires
        boolean account_setup_completed
        string pending_email
        string email_change_token
        timestamp email_change_expires
    }
    
    user_preferences {
        int id PK
        int user_id FK
        enum measurement_system
        json dietary_restrictions
        json allergens
        boolean email_notifications
        enum default_visibility
        string theme
    }
    
    password_reset_tokens {
        int id PK
        int user_id FK
        string token UK
        timestamp expires_at
        boolean used
        timestamp created_at
    }
    
    user_stats {
        int user_id PK_FK
        int recipe_count
        int public_recipe_count
        int private_recipe_count
        int collection_count
        int total_recipe_views
        int total_recipe_favorites
        decimal average_recipe_rating
        timestamp created_at
        timestamp updated_at
    }
    
    recipes {
        int id PK
        int user_id FK
        string name
        text description
        text instructions
        text notes
        int prep_time
        int cook_time
        int total_time
        string servings
        enum difficulty
        enum visibility
        string slug UK
        string meta_description
        json ingredients_json
        timestamp created_at
        timestamp updated_at
        timestamp published_at
    }
    
    recipe_sources {
        int id PK
        int recipe_id FK_UK
        string source_name
        text source_url
        string author
        string issue
        enum imported_from
        timestamp imported_at
        int source_url_confidence
        string source_url_detection_method
    }
    
    recipe_photos {
        int id PK
        int recipe_id FK
        string photo_url
        enum photo_type
        text caption
        int step_number
        int sort_order
        timestamp created_at
    }
    
    recipe_stats {
        int recipe_id PK_FK
        int view_count
        int unique_view_count
        int favorite_count
        int rating_count
        decimal average_rating
        int review_count
        int email_share_count
        int print_count
        timestamp last_viewed_at
        timestamp updated_at
    }
    
    ingredients {
        int id PK
        string name UK
        string plural_name
        string category
        string subcategory
        json aliases
        boolean is_common
        json allergen_info
        json nutritional_data
        string default_unit
        text storage_tips
        json substitution_suggestions
        json seasonal_info
        int usage_count
        timestamp created_at
        timestamp updated_at
    }
    
    recipe_ingredients {
        int id PK
        int recipe_id FK
        int ingredient_id FK
        string amount
        string unit
        string preparation
        boolean is_optional
        text notes
        int sort_order
        string ingredient_group
    }
    
    user_ingredient_substitutions {
        int id PK
        int user_id FK
        int original_ingredient_id FK
        int substitute_ingredient_id FK
        string reason
        boolean auto_apply
        timestamp created_at
    }
    
    tags {
        int id PK
        string name
        string slug
        enum tag_scope
        int user_id FK
        text description
        enum tag_type
        string icon
        timestamp created_at
    }
    
    recipe_tags {
        int recipe_id PK_FK
        int tag_id PK_FK
    }
    
    recipe_favorites {
        int id PK
        int user_id FK
        int recipe_id FK
        text personal_notes
        timestamp created_at
    }
    
    recipe_ratings {
        int id PK
        int user_id FK
        int recipe_id FK
        decimal rating
        text review
        text modifications
        boolean would_make_again
        timestamp created_at
        timestamp updated_at
    }
    
    collections {
        int id PK
        int user_id FK
        string name
        text description
        string cover_photo_url
        enum visibility
        timestamp created_at
        timestamp updated_at
    }
    
    collection_recipes {
        int collection_id PK_FK
        int recipe_id PK_FK
        int sort_order
        text personal_notes
        timestamp added_at
    }
    
    meal_plans {
        int id PK
        int user_id FK
        string name
        date start_date
        date end_date
        text notes
        timestamp created_at
        timestamp updated_at
    }
    
    meal_plan_recipes {
        int id PK
        int meal_plan_id FK
        int recipe_id FK
        date planned_date
        enum meal_type
        int servings_planned
        text notes
        boolean completed
        timestamp completed_at
    }
    
    recipe_email_log {
        int id PK
        int recipe_id FK
        int sent_by_user_id FK
        string recipient_email
        string recipient_name
        text message
        timestamp sent_at
    }
```

---

## Simplified Visual Schema (ASCII Art)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RECIPE EDITOR DATABASE                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ USER MANAGEMENT CLUSTER                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐         ┌──────────────────────┐                         │
│  │    users     │────────▶│  user_preferences    │                         │
│  │   (core)     │   1:1   │   (settings)         │                         │
│  └──────┬───────┘         └──────────────────────┘                         │
│         │                                                                    │
│         │ 1:N             ┌──────────────────────┐                         │
│         ├────────────────▶│password_reset_tokens │                         │
│         │                 │   (temp security)    │                         │
│         │                 └──────────────────────┘                         │
│         │                                                                    │
│         │ 1:1             ┌──────────────────────┐                         │
│         └────────────────▶│    user_stats        │                         │
│                           │  (cached counts)     │                         │
│                           └──────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ RECIPE CORE CLUSTER                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐         ┌──────────────────────┐                         │
│  │    users     │────────▶│      recipes         │                         │
│  │              │   1:N   │   (main content)     │                         │
│  └──────────────┘         └──────┬───────────────┘                         │
│                                   │                                          │
│                                   │ 1:1                                      │
│                                   ├──────────────▶ recipe_sources           │
│                                   │                (attribution)             │
│                                   │                                          │
│                                   │ 1:N                                      │
│                                   ├──────────────▶ recipe_photos             │
│                                   │                (images)                  │
│                                   │                                          │
│                                   │ 1:1                                      │
│                                   ├──────────────▶ recipe_stats              │
│                                   │                (analytics)               │
│                                   │                                          │
│                                   │ N:M                                      │
│                                   └──────────────▶ recipe_ingredients        │
│                                                    (via junction)            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ INGREDIENT SYSTEM CLUSTER                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐         ┌─────────────────────────┐                  │
│  │   ingredients    │◀────────│  recipe_ingredients     │                  │
│  │   (catalog)      │   N:M   │   (measurements)        │                  │
│  └────────┬─────────┘         └─────────┬───────────────┘                  │
│           │                              │                                   │
│           │                              │                                   │
│           │                         ┌────┴─────────┐                        │
│           │                         │   recipes    │                        │
│           │                         └──────────────┘                        │
│           │                                                                  │
│           │ N:M                                                              │
│           └──────────────────────▶ user_ingredient_substitutions            │
│                                    (personal replacements)                   │
│                                              ▲                               │
│                                              │                               │
│                                         ┌────┴─────┐                        │
│                                         │  users   │                        │
│                                         └──────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TAG SYSTEM CLUSTER (Updated: System + Personal Tags)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐                                                           │
│  │    users     │────────────────────┐                                      │
│  │              │   1:N (personal)   │                                      │
│  └──────────────┘                    │                                      │
│                                      ▼                                       │
│                           ┌──────────────────┐                              │
│                           │      tags        │                              │
│                           │ tag_scope: enum  │                              │
│                           │  - system        │                              │
│                           │  - personal      │                              │
│                           └────────┬─────────┘                              │
│                                    │                                         │
│                                    │ N:M                                     │
│                                    │                                         │
│  ┌──────────────┐         ┌────────▼─────────┐        ┌──────────────┐    │
│  │   recipes    │◀────────│   recipe_tags    │───────▶│     tags     │    │
│  │              │   N:M   │   (junction)     │   N:M  │              │    │
│  └──────────────┘         └──────────────────┘        └──────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ USER INTERACTIONS CLUSTER                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                    ┌─────────────────────┐                                  │
│                    │      recipes        │                                  │
│                    └──────┬───────┬──────┘                                  │
│                           │       │                                          │
│         ┌─────────────────┘       └──────────────────┐                     │
│         │                                             │                     │
│         │ N:1                                    N:1 │                     │
│         │                                             │                     │
│  ┌──────▼──────────┐                      ┌──────────▼──────┐              │
│  │recipe_favorites │                      │ recipe_ratings  │              │
│  │                 │                      │                 │              │
│  └──────┬──────────┘                      └──────┬──────────┘              │
│         │                                         │                         │
│         │ N:1                                N:1 │                         │
│         │                                         │                         │
│         │         ┌──────────────┐               │                         │
│         └────────▶│    users     │◀──────────────┘                         │
│                   └──────────────┘                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ COLLECTIONS/COOKBOOKS CLUSTER                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐         ┌────────────────────┐                           │
│  │    users     │────────▶│    collections     │                           │
│  │              │   1:N   │   (cookbooks)      │                           │
│  └──────────────┘         └─────────┬──────────┘                           │
│                                      │                                       │
│                                      │ 1:N                                   │
│                                      ▼                                       │
│                           ┌────────────────────┐        ┌──────────────┐   │
│                           │collection_recipes  │───────▶│   recipes    │   │
│                           │   (junction)       │  N:1   │              │   │
│                           └────────────────────┘        └──────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ MEAL PLANNING CLUSTER                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐         ┌────────────────────┐                           │
│  │    users     │────────▶│   meal_plans       │                           │
│  │              │   1:N   │  (weekly/monthly)  │                           │
│  └──────────────┘         └─────────┬──────────┘                           │
│                                      │                                       │
│                                      │ 1:N                                   │
│                                      ▼                                       │
│                           ┌────────────────────┐        ┌──────────────┐   │
│                           │meal_plan_recipes   │───────▶│   recipes    │   │
│                           │  (scheduled)       │  N:1   │              │   │
│                           └────────────────────┘        └──────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TRACKING & LOGGING                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐                                                           │
│  │    users     │──┐                                                        │
│  │              │  │                                                        │
│  └──────────────┘  │ 1:N                                                    │
│                    │                                                         │
│                    │         ┌──────────────┐                               │
│  ┌──────────────┐ └────────▶│   recipes    │                               │
│  │   recipes    │           │              │                               │
│  │              │──────────▶└──────────────┘                               │
│  └──────────────┘    1:N                                                    │
│         │                           │                                        │
│         │                           │ N:1                                    │
│         │ 1:N                       ▼                                        │
│         │                  ┌─────────────────┐                              │
│         └─────────────────▶│recipe_email_log │                              │
│                            │  (email audit)  │                              │
│                            └─────────────────┘                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Statistics

### Table Count by Category:

| Category | Tables | Description |
|----------|--------|-------------|
| **User Management** | 4 | users, user_preferences, password_reset_tokens, user_stats |
| **Recipes** | 4 | recipes, recipe_sources, recipe_photos, recipe_stats |
| **Ingredients** | 3 | ingredients, recipe_ingredients, user_ingredient_substitutions |
| **Tags** | 2 | tags, recipe_tags |
| **User Interactions** | 3 | recipe_favorites, recipe_ratings, collections (+1 junction) |
| **Meal Planning** | 2 | meal_plans, meal_plan_recipes |
| **Tracking** | 1 | recipe_email_log |
| **Total** | **19 tables** | (14 entity tables + 5 junction tables) |

---

## Key Relationships

### One-to-Many (1:N)
- **users → recipes** (user owns many recipes)
- **users → collections** (user creates many collections)
- **users → meal_plans** (user creates many meal plans)
- **users → tags** (user owns many personal tags)
- **recipes → recipe_ingredients** (recipe has many ingredients)
- **recipes → recipe_photos** (recipe has many photos)
- **ingredients → recipe_ingredients** (ingredient used in many recipes)

### Many-to-Many (N:M)
- **recipes ↔ tags** (via recipe_tags junction)
- **recipes ↔ ingredients** (via recipe_ingredients junction)
- **collections ↔ recipes** (via collection_recipes junction)
- **meal_plans ↔ recipes** (via meal_plan_recipes junction)

### One-to-One (1:1)
- **users → user_preferences** (each user has one preference set)
- **users → user_stats** (each user has one stats record)
- **recipes → recipe_sources** (each recipe has one source)
- **recipes → recipe_stats** (each recipe has one stats record)

---

## Tag System Details (NEW)

### Tag Ownership Model:

```
┌─────────────────────────────────────────┐
│             tags                         │
├─────────────────────────────────────────┤
│ id          | tag_scope  | user_id      │
├─────────────────────────────────────────┤
│ 1           | system     | NULL         │ ← Available to all users
│ 2           | personal   | 5            │ ← Only visible to user 5
│ 3           | personal   | 5            │ ← Another personal tag for user 5
│ 4           | personal   | 8            │ ← Only visible to user 8
│ 5           | system     | NULL         │ ← Available to all users
└─────────────────────────────────────────┘

Rules:
- System tags: user_id = NULL, visible to all
- Personal tags: user_id = owner, visible only to that user
- Multiple users can have personal tags with same name
```

---

## Data Flow Examples

### Example 1: Creating a Recipe

```
1. User creates recipe
   users.id → recipes.user_id

2. Recipe created
   recipes.id generated

3. Recipe stats initialized
   recipes.id → recipe_stats.recipe_id (TRIGGER)

4. User stats updated
   users.id → user_stats.user_id (TRIGGER: recipe_count++)

5. Ingredients added
   recipes.id + ingredients.id → recipe_ingredients

6. Ingredient usage updated
   ingredients.usage_count++ (TRIGGER)

7. Tags added (personal tags)
   recipes.id + tags.id → recipe_tags
   tags.user_id = current_user.id

8. Source info added (if provided)
   recipes.id → recipe_sources.recipe_id
```

### Example 2: User Favorites Recipe

```
1. User clicks favorite
   users.id + recipes.id → recipe_favorites

2. Recipe favorite count updated
   recipe_stats.favorite_count++ (TRIGGER)

3. User stats updated
   user_stats.total_recipe_favorites++ (if implemented)
```

### Example 3: Converting Personal Tag to System

```
Before:
tags (id=5, name="DINNER", tag_scope="personal", user_id=1)
tags (id=8, name="DINNER", tag_scope="personal", user_id=3)

After conversion:
tags (id=10, name="DINNER", tag_scope="system", user_id=NULL)
[Old tags deleted, recipe_tags updated to point to id=10]
```

---

## Indexes and Performance

### Primary Indexes (PK):
- All tables have auto-increment integer primary keys

### Foreign Key Indexes:
- Automatically created on all FK columns for join performance

### Search Indexes:
- **FULLTEXT**: recipes (name, description, instructions, notes)
- **FULLTEXT**: ingredients (name, plural_name)
- **Composite**: Various for common query patterns

### Special Indexes:
- `idx_user_created` on recipes: (user_id, created_at DESC)
- `idx_recipe_rating` on recipe_ratings: (recipe_id, rating DESC)
- `idx_popular` on recipe_stats: (favorite_count DESC, average_rating DESC)

---

## Cascade Delete Behavior

| Parent Table | Child Table | Behavior |
|--------------|-------------|----------|
| users | recipes | CASCADE (delete user → delete recipes) |
| users | user_preferences | CASCADE |
| users | tags (personal) | CASCADE |
| recipes | recipe_ingredients | CASCADE |
| recipes | recipe_photos | CASCADE |
| recipes | recipe_tags | CASCADE |
| recipes | recipe_favorites | CASCADE |
| ingredients | recipe_ingredients | RESTRICT (can't delete if used) |
| tags | recipe_tags | CASCADE |

---

## Storage Considerations

### Typical Storage Sizes (1000 recipes, 100 users):

| Table | Estimated Size | Notes |
|-------|----------------|-------|
| recipes | 5-10 MB | Main content |
| recipe_ingredients | 2-5 MB | Many-to-many |
| ingredients | 1-2 MB | Master catalog |
| tags | <1 MB | Small catalog |
| recipe_tags | <1 MB | Junction table |
| users | <1 MB | User accounts |
| recipe_photos | <1 MB | URLs only, not images |
| Others | 1-3 MB | Stats, logs, etc. |
| **Total** | **15-25 MB** | Database only (no images) |

*Note: Actual recipe photos stored in filesystem, not database*

---

## JSON Field Contents

### users.dietary_restrictions
```json
["vegetarian", "nut-free", "dairy-free"]
```

### ingredients.aliases
```json
["cilantro", "coriander leaves", "chinese parsley"]
```

### recipes.ingredients_json
```json
[
  {"description": "flour", "amount": "2", "unit": "cups"},
  {"description": "sugar", "amount": "1", "unit": "cup"}
]
```

---

## Views Available

1. **recipe_detail_view**: Complete recipe with owner, source, tags, stats
2. **user_favorites_view**: User's favorited recipes with details
3. **popular_ingredients_view**: Ingredients ranked by usage

---

## To Visualize This Diagram:

### Option 1: Mermaid Live Editor
1. Visit: https://mermaid.live/
2. Copy the Mermaid code block from above
3. Paste into editor
4. Export as PNG/SVG

### Option 2: GitHub/GitLab
- The Mermaid diagram renders automatically in markdown files

### Option 3: Draw.io / Lucidchart
- Use the ASCII art as reference
- Create professional diagram with drag-and-drop

### Option 4: Database Tools
```bash
# MySQL Workbench can reverse-engineer from database
# Or use online tools like dbdiagram.io
```

---

## Quick Table Reference

```
Core Tables (must exist):
- users ✓
- recipes ✓
- ingredients ✓

Junction Tables (many-to-many):
- recipe_tags ✓
- recipe_ingredients ✓
- collection_recipes ✓
- meal_plan_recipes ✓

Support Tables:
- user_preferences
- password_reset_tokens
- recipe_sources
- recipe_photos
- recipe_stats
- user_stats
- tags
- recipe_favorites
- recipe_ratings
- collections
- meal_plans
- user_ingredient_substitutions
- recipe_email_log
```

---

**Total Database Entities**: 19 tables + 3 views + 8 triggers

