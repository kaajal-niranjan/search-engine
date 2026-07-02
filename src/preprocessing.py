"""Data preparation: catalog generation, cleaning, and exploratory analysis."""

from __future__ import annotations

import logging
import random
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.config import (
    CLEAN_CATALOG_PATH,
    DATA_DIR,
    EDA_REPORT_PATH,
    RAW_CATALOG_PATH,
    RANDOM_SEED,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synthetic catalog templates
# ---------------------------------------------------------------------------

CATEGORIES = {
    "Electronics": {
        "templates": [
            ("Wireless Bluetooth Headphones", "Premium over-ear headphones with active noise cancellation, 30-hour battery life, and deep bass for music lovers."),
            ("4K Smart LED TV 55 inch", "Ultra HD television with HDR10, built-in streaming apps, and voice control for home entertainment."),
            ("USB-C Laptop Charger 65W", "Fast charging adapter compatible with most ultrabooks and tablets, compact travel design."),
            ("Mechanical Gaming Keyboard RGB", "Tactile switches, per-key RGB lighting, and programmable macros for competitive gaming."),
            ("Portable Power Bank 20000mAh", "High-capacity external battery with dual USB ports and fast charge support for phones and tablets."),
            ("Wireless Mouse Ergonomic", "Silent click wireless mouse with adjustable DPI and long-range Bluetooth connectivity."),
            ("Smart Home Security Camera", "1080p indoor camera with night vision, motion alerts, and two-way audio via mobile app."),
            ("Noise Cancelling Earbuds", "True wireless earbuds with transparency mode and sweat resistance for workouts."),
            ("Tablet Stand Adjustable", "Aluminum foldable stand for tablets and e-readers, ideal for desk and kitchen use."),
            ("HDMI Cable 6ft 4K", "High-speed HDMI 2.0 cable supporting 4K at 60Hz for monitors and projectors."),
        ],
        "price_range": (15, 899),
    },
    "Clothing": {
        "templates": [
            ("Men's Winter Puffer Jacket", "Insulated warm jacket with water-resistant shell, perfect for cold weather trips and outdoor hiking."),
            ("Women's Fleece Lined Leggings", "Thermal leggings with soft fleece interior for cozy winter layering and yoga."),
            ("Cotton Crew Neck T-Shirt Pack", "Breathable everyday tees in assorted colors, machine washable and durable."),
            ("Waterproof Rain Jacket Unisex", "Lightweight packable rain shell with hood, ideal for travel and commuting."),
            ("Wool Blend Sweater", "Classic knit pullover with ribbed cuffs, warm and stylish for fall and winter."),
            ("Running Shorts Quick Dry", "Lightweight athletic shorts with moisture-wicking fabric and inner liner."),
            ("Denim Jacket Classic Fit", "Timeless denim outerwear with button closure, versatile casual layer."),
            ("Thermal Base Layer Top", "Moisture-wicking base layer for skiing, snowboarding, and winter sports."),
            ("Sun Protection UV Shirt", "Long sleeve UPF 50+ shirt for beach, fishing, and outdoor activities."),
            ("Merino Wool Hiking Socks", "Cushioned wool socks that regulate temperature on long trail hikes."),
        ],
        "price_range": (12, 249),
    },
    "Home & Kitchen": {
        "templates": [
            ("Stainless Steel Cookware Set 10-Piece", "Non-stick pots and pans with even heat distribution for everyday cooking."),
            ("Programmable Coffee Maker", "12-cup drip coffee machine with timer, reusable filter, and auto shut-off."),
            ("Memory Foam Pillow Queen", "Ergonomic cervical support pillow for better sleep and neck alignment."),
            ("Robot Vacuum Cleaner", "Smart mapping vacuum with app control, ideal for pet hair on hardwood and carpet."),
            ("Ceramic Nonstick Frying Pan", "Induction-compatible skillet with PFOA-free coating for healthy cooking."),
            ("Electric Kettle 1.7L", "Fast-boil stainless kettle with auto shut-off for tea and instant meals."),
            ("Bamboo Cutting Board Set", "Eco-friendly boards in three sizes with juice grooves for meal prep."),
            ("Air Fryer 5 Quart", "Digital air fryer for crispy meals with less oil, includes recipe booklet."),
            ("Weighted Blanket 15lb", "Calming blanket for improved sleep quality and reduced anxiety."),
            ("Glass Food Storage Containers", "BPA-free meal prep containers with snap-lock lids, microwave safe."),
        ],
        "price_range": (18, 349),
    },
    "Sports & Outdoors": {
        "templates": [
            ("Camping Tent 4-Person", "Waterproof dome tent with easy setup, ventilation windows, and rainfly for family trips."),
            ("Yoga Mat Non-Slip 6mm", "Extra thick exercise mat with carrying strap for yoga, pilates, and floor workouts."),
            ("Adjustable Dumbbell Set", "Space-saving adjustable weights from 5 to 52.5 lbs for home strength training."),
            ("Hiking Backpack 40L", "Ergonomic trekking pack with hydration sleeve and rain cover for multi-day hikes."),
            ("Insulated Water Bottle 32oz", "Double-wall stainless bottle keeps drinks cold 24 hours, hot 12 hours."),
            ("Resistance Bands Set", "Five latex bands with handles and door anchor for full-body home workouts."),
            ("Folding Camping Chair", "Portable outdoor chair with cup holder, lightweight for beach and tailgating."),
            ("Cycling Helmet Adult", "Ventilated road bike helmet with adjustable fit system and MIPS protection."),
            ("Sleeping Bag 3-Season", "Compact mummy bag rated to 20°F for backpacking and car camping."),
            ("Trail Running Shoes", "Lightweight grippy soles with cushioned midsole for rocky and muddy trails."),
        ],
        "price_range": (20, 399),
    },
    "Beauty & Personal Care": {
        "templates": [
            ("Vitamin C Face Serum", "Brightening antioxidant serum to reduce dark spots and improve skin radiance."),
            ("Hydrating Moisturizer SPF 30", "Daily facial lotion with broad spectrum sun protection and hyaluronic acid."),
            ("Electric Toothbrush Rechargeable", "Sonic brush with multiple modes and two-minute timer for dental health."),
            ("Argan Oil Hair Treatment", "Nourishing leave-in oil to repair dry damaged hair and reduce frizz."),
            ("Retinol Night Cream", "Anti-aging night moisturizer to smooth fine lines and even skin tone."),
            ("Coconut Body Lotion", "Rich moisturizing lotion with natural coconut extract for soft smooth skin."),
            ("Makeup Brush Set 12-Piece", "Synthetic bristle brushes for foundation, blush, and eye makeup application."),
            ("Beard Grooming Kit", "Trimming oil, balm, and comb set for beard care and styling."),
            ("Exfoliating Face Scrub", "Gentle walnut scrub to remove dead skin cells and unclog pores."),
            ("Lip Balm SPF 15 Pack", "Moisturizing lip protection with vitamin E for daily outdoor use."),
        ],
        "price_range": (8, 89),
    },
    "Books & Stationery": {
        "templates": [
            ("Productivity Planner 2026", "Undated daily planner with goal tracking, habit pages, and monthly reviews."),
            ("Hardcover Notebook A5 Ruled", "200-page journal with thick paper suitable for fountain pens and bullet journaling."),
            ("Beginner Python Programming Guide", "Hands-on coding book covering fundamentals, data structures, and projects."),
            ("Meditation and Mindfulness Workbook", "Guided exercises for stress relief, breathing techniques, and daily calm."),
            ("Colored Pencil Art Set 48 Colors", "Professional grade pencils with blending tools for drawing and sketching."),
            ("Sticky Notes Assorted Pack", "Neon and pastel repositionable notes for office and study organization."),
            ("Classic Novel Collection Box Set", "Timeless literature anthology with embossed hardcover bindings."),
            ("Calligraphy Pen Set", "Dip pens, ink, and practice sheets for hand lettering beginners."),
            ("Desk Organizer Bamboo", "Multi-compartment tray for pens, phones, and office supplies."),
            ("Children's Illustrated Storybook", "Colorful picture book with moral tales for bedtime reading ages 4-8."),
        ],
        "price_range": (6, 45),
    },
    "Toys & Games": {
        "templates": [
            ("Building Blocks STEM Kit 500pc", "Creative construction set encouraging engineering skills for kids ages 6+."),
            ("Family Board Game Strategy", "Award-winning tabletop game for 2-4 players, 45-minute play time."),
            ("Remote Control Car Off-Road", "Rechargeable RC truck with shock absorbers for indoor and outdoor play."),
            ("Jigsaw Puzzle 1000 Pieces Landscape", "Challenging adult puzzle featuring scenic mountain lake photography."),
            ("Plush Teddy Bear Large", "Soft hypoallergenic stuffed animal gift for toddlers and collectors."),
            ("Educational Science Experiment Kit", "Safe chemistry and physics experiments with illustrated guide for young scientists."),
            ("Card Game Party Pack", "Fast-paced multiplayer card game suitable for ages 10 and up."),
            ("Wooden Chess Set Foldable", "Handcrafted chess board with storage for pieces, travel friendly."),
            ("Art and Craft Supply Box", "Glitter, glue, scissors, and paper assortment for creative kids projects."),
            ("Outdoor Bubble Machine", "Battery-powered bubble blower for birthday parties and backyard fun."),
        ],
        "price_range": (10, 79),
    },
    "Health & Wellness": {
        "templates": [
            ("Foam Roller Muscle Recovery", "High-density roller for myofascial release after workouts and physical therapy."),
            ("Digital Body Weight Scale", "Bluetooth smart scale tracking weight, BMI, and body composition trends."),
            ("Essential Oil Diffuser Ultrasonic", "Aromatherapy humidifier with LED mood lighting and timer settings."),
            ("Yoga Block and Strap Set", "Cork blocks and cotton strap to improve flexibility and alignment in poses."),
            ("Protein Powder Whey Isolate", "Low-carb post-workout supplement with 25g protein per serving, vanilla flavor."),
            ("Blue Light Blocking Glasses", "Computer glasses reducing eye strain during long screen sessions."),
            ("Massage Gun Percussion", "Cordless deep tissue massager with adjustable speeds for muscle soreness relief."),
            ("Herbal Sleep Tea Blend", "Caffeine-free chamomile and valerian tea for relaxing bedtime routine."),
            ("Posture Corrector Back Brace", "Adjustable shoulder support to improve desk posture and reduce slouching."),
            ("Fitness Tracker Watch", "Heart rate, step count, sleep monitoring, and smartphone notifications on wrist."),
        ],
        "price_range": (12, 199),
    },
}


def _clean_text(text: str) -> str:
    """Normalize whitespace and strip HTML-like tags from text."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def generate_synthetic_catalog(n_products: int = 800, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate a synthetic e-commerce product catalog."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    rows: list[dict] = []
    product_id = 1
    all_templates: list[tuple[str, str, str, tuple[int, int]]] = []

    for category, meta in CATEGORIES.items():
        for title, description in meta["templates"]:
            all_templates.append((category, title, description, meta["price_range"]))

    while len(rows) < n_products:
        category, base_title, base_description, price_range = rng.choice(all_templates)
        variant_suffixes = ["", " Pro", " Plus", " Lite", " Deluxe", " Essential", " Ultra", " Classic"]
        color_variants = ["", " - Black", " - White", " - Navy", " - Gray", " - Red"]
        suffix = rng.choice(variant_suffixes)
        color = rng.choice(color_variants) if rng.random() > 0.5 else ""

        title = f"{base_title}{suffix}{color}".strip()
        description = base_description
        if rng.random() > 0.6:
            extras = [
                "Free shipping eligible.",
                "Highly rated by customers.",
                "Limited time offer.",
                "Best seller in category.",
                "Eco-friendly packaging.",
            ]
            description = f"{description} {rng.choice(extras)}"

        low, high = price_range
        price = round(float(np_rng.uniform(low, high)), 2)
        rating = round(float(np.clip(np_rng.normal(4.2, 0.5), 2.5, 5.0)), 1)

        rows.append(
            {
                "id": product_id,
                "title": title,
                "description": description,
                "category": category,
                "price": price,
                "rating": rating,
            }
        )
        product_id += 1

    df = pd.DataFrame(rows)
    logger.info("Generated %d synthetic products", len(df))
    return df


class DataPreprocessor:
    """Load, clean, and explore product catalog data."""

    def __init__(self, raw_path: Path = RAW_CATALOG_PATH, clean_path: Path = CLEAN_CATALOG_PATH):
        self.raw_path = raw_path
        self.clean_path = clean_path

    def ensure_catalog(self, n_products: int = 800) -> pd.DataFrame:
        """Create raw catalog if missing and return DataFrame."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.raw_path.exists():
            logger.info("Raw catalog not found; generating synthetic data...")
            df = generate_synthetic_catalog(n_products=n_products)
            df.to_csv(self.raw_path, index=False)
        return pd.read_csv(self.raw_path)

    def clean(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Clean text fields and engineer search_text column."""
        if df is None:
            df = self.ensure_catalog()

        df = df.copy()
        required = {"id", "title", "description", "category", "price", "rating"}
        missing_cols = required - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        df["title"] = df["title"].fillna("").apply(_clean_text)
        df["description"] = df["description"].fillna("").apply(_clean_text)
        df["category"] = df["category"].fillna("Unknown").apply(_clean_text)

        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df["price"] = df["price"].fillna(df["price"].median())
        df["rating"] = df["rating"].fillna(df["rating"].median())

        df["search_text"] = (
            df["title"] + ". " + df["description"] + ". Category: " + df["category"]
        ).str.strip()

        df = df.drop_duplicates(subset=["id"]).reset_index(drop=True)
        df.to_csv(self.clean_path, index=False)
        logger.info("Saved cleaned catalog to %s (%d products)", self.clean_path, len(df))
        return df

    def run_eda(self, df: Optional[pd.DataFrame] = None) -> str:
        """Explore dataset and write EDA report."""
        if df is None:
            if self.clean_path.exists():
                df = pd.read_csv(self.clean_path)
            else:
                df = self.clean(self.ensure_catalog())

        lines = [
            "=" * 60,
            "EXPLORATORY DATA ANALYSIS REPORT",
            "=" * 60,
            f"\nTotal products: {len(df)}",
            f"Columns: {list(df.columns)}",
            "\n--- Missing Values ---",
            df.isnull().sum().to_string(),
            "\n--- Price Statistics ---",
            df["price"].describe().to_string(),
            "\n--- Rating Statistics ---",
            df["rating"].describe().to_string(),
            "\n--- Category Distribution ---",
            df["category"].value_counts().to_string(),
            "\n--- Search Text Length (chars) ---",
            df["search_text"].str.len().describe().to_string(),
        ]
        report = "\n".join(lines)
        EDA_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        EDA_REPORT_PATH.write_text(report, encoding="utf-8")
        logger.info("EDA report saved to %s", EDA_REPORT_PATH)
        return report


def run_preprocessing(n_products: int = 800) -> pd.DataFrame:
    """End-to-end preprocessing pipeline."""
    preprocessor = DataPreprocessor()
    raw_df = preprocessor.ensure_catalog(n_products=n_products)
    clean_df = preprocessor.clean(raw_df)
    preprocessor.run_eda(clean_df)
    return clean_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    run_preprocessing()
