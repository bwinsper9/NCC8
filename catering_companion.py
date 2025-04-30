import streamlit as st
import pandas as pd
import random
import time
from fpdf import FPDF
import tempfile
from fuzzywuzzy import fuzz

# Kitchen affirmations
affirmations = [
    "You're going to have a great event today!",
    "September is coming. Rest is near!",
    "You're doing great work, keep pushing.",
    "Big events start with small prep wins.",
    "Your mise en place is your superpower.",
    "Stay sharp. Stay strong. Stay caffeinated ☕️.",
    "Organization is the secret ingredient.",
    "The guests won't know, but your team will. Great work!",
    "Good prep saves lives (and lunch rushes).",
    "Every tray you prep is a step closer to success.",
    "Take pride in every tray, every plate, every garnish.",
    "Today's prep is tomorrow's peace.",
    "Keep those knives sharp and your spirits sharper."
]

def scale_recipe(recipe_df, number_of_guests):
    base_servings = recipe_df["BaseServings"].iloc[0]
    scale_factor = number_of_guests / base_servings
    recipe_df["ScaledQuantity"] = recipe_df["Quantity"] * scale_factor
    return recipe_df

def format_shopping_list(scaled_df):
    sections = {}
    grouped = scaled_df.groupby(["Category"])
    for category, group in grouped:
        lines = []
        for _, row in group.sort_values("Ingredient").iterrows():
            quantity = row["ScaledQuantity"]
            ingredient = row["Ingredient"]
            unit = row["Unit"]
            lines.append(f"{quantity} {unit} {ingredient}")
        sections[category] = lines
    return sections

class PDFThreeColumns(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Catering Companion - Shopping List", ln=True, align="C")
        self.ln(5)

    def chapter_title(self, title):
        title = title[0] if isinstance(title, tuple) else title
        title = title.upper()
        self.set_font("Arial", "B", 12)
        self.set_text_color(0)
        self.cell(0, 8, title, ln=True, align="L")
        self.ln(2)

    def chapter_body(self, lines):
        self.set_font("Arial", "", 10)
        self.set_text_color(50)
        column_width = 60
        line_height = 7
        count = 0
        for line in lines:
            if line.strip():
                x = self.get_x()
                y = self.get_y()
                self.rect(x, y + 1.5, 3.5, 3.5)
                self.cell(7)
                try:
                    parts = line.strip().split(' ', 2)
                    qty = float(parts[0])
                    unit = parts[1]
                    item = parts[2]
                    if qty.is_integer():
                        qty_display = f"{int(qty)}"
                    else:
                        qty_display = f"{qty}"
                    self.cell(column_width - 7, line_height, f"{qty_display} {unit} {item}", ln=0)
                except:
                    self.cell(column_width - 7, line_height, line.strip(), ln=0)

                count += 1
                if count % 3 == 0:
                    self.ln(line_height)
                else:
                    self.set_xy(x + column_width, y)
        self.ln(8)

class PDFRecipeGuides(FPDF):
    def header(self):
        pass
    def recipe_title(self, title):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(0)
        clean_title = title.upper()
        self.cell(0, 10, clean_title, ln=True, align='C')
        self.ln(8)
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Catering Companion - Recipe Guide", ln=True, align="C")
        self.ln(5)

    def recipe_title(self, title):
        self.set_font("Arial", "B", 16)
        self.set_text_color(0)
        clean_title = title.upper()
        self.cell(0, 10, clean_title, ln=True, align="C")
        self.ln(8)

    def consolidate_unit(self, qty, unit):
        qty = float(qty)
        new_unit = unit.lower()
        if new_unit == 'g' and qty >= 1000:
            return qty / 1000, 'kg'
        elif new_unit == 'ml' and qty >= 1000:
            return qty / 1000, 'l'
        elif new_unit == 'oz' and qty >= 16:
            return qty / 16, 'lb'
        elif new_unit == 'cups' and qty >= 4:
            return qty / 4, 'quarts'
        elif new_unit == 'cups' and qty >= 2:
            return qty / 2, 'pints'
        elif new_unit == 'tsp' and qty >= 3:
            return qty / 3, 'tbsp'
        elif new_unit == 'tbsp' and qty >= 2:
            return qty / 2, 'oz'
        elif new_unit == 'oz' and qty >= 32:
            return qty / 32, 'quarts'
        elif new_unit == 'oz' and qty >= 128:
            return qty / 128, 'gallons'
        else:
            return qty, unit

    def recipe_ingredients(self, ingredients):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Ingredients:", ln=True, align="L")
        self.set_font("Arial", "", 11)
        for qty, unit, item in ingredients:
            qty_display, new_unit = self.consolidate_unit(qty, unit)
            if float(qty_display).is_integer():
                qty_display = int(qty_display)
            self.cell(0, 8, f"- {qty_display} {new_unit} {item}", ln=True)
        self.ln(5)

    def recipe_method(self, method_text):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Method:", ln=True, align="L")
        self.set_font("Arial", "", 11)
        self.multi_cell(0, 8, method_text)
        self.ln(5)

def generate_shopping_list_pdf(sections):
    pdf = PDFThreeColumns()
    pdf.add_page()
    for category, lines in sections.items():
        pdf.chapter_title(category)
        pdf.chapter_body(lines)
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_pdf.name)
    return temp_pdf.name

def generate_recipe_guides_pdf(recipe_guides):
    pdf = PDFRecipeGuides()
    pdf.set_auto_page_break(auto=True, margin=15)
    for recipe_name, (ingredients_list, method_text) in recipe_guides.items():
        pdf.add_page()
        pdf.recipe_title(recipe_name)
        pdf.recipe_ingredients(ingredients_list)
        pdf.recipe_method(method_text)
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_pdf.name)
    return temp_pdf.name

# Streamlit App
st.set_page_config(page_title="Catering Companion", page_icon="🍴", layout="centered")

try:
    recipes_df = pd.read_csv("master_recipe_template.csv")
    available_recipes = sorted(recipes_df["RecipeName"].unique())

    guests = st.number_input("Number of guests", min_value=1, step=1)
    selected = st.multiselect("Select recipes", options=available_recipes)

    if st.button("Generate Plan") and selected and guests > 0:
        st.write("✨ " + random.choice(affirmations))
        with st.spinner("Scaling recipes and building your PDFs..."):
            time.sleep(1)

            combined_scaled = pd.DataFrame()
            individual_scaled = {}
            methods = {}

            for recipe_name in selected:
                data = recipes_df[recipes_df["RecipeName"].str.lower() == recipe_name.lower()]
                scaled = scale_recipe(data, guests)
                combined_scaled = pd.concat([combined_scaled, scaled], ignore_index=True)
                individual_scaled[recipe_name] = scaled
                methods[recipe_name] = data["Method"].iloc[0]

            combined_scaled = combined_scaled.groupby(
                ["Ingredient", "Unit", "Category"], as_index=False
            ).sum()

            sections = format_shopping_list(combined_scaled)

            recipe_guides = {}
            for recipe_name, scaled_data in individual_scaled.items():
                ingredients_list = []
                for _, row in scaled_data.sort_values("Ingredient").iterrows():
                    ingredients_list.append((round(row["ScaledQuantity"], 2), row["Unit"], row["Ingredient"]))
                recipe_guides[recipe_name] = (ingredients_list, methods[recipe_name])

            shop_pdf = generate_shopping_list_pdf(sections)
            recipe_pdf = generate_recipe_guides_pdf(recipe_guides)

            
    
    st.markdown("### ✅ Shopping List and Recipe Guides have been generated.")

    # Show Shopping List on screen
    st.markdown("## 🛒 Shopping List Preview")
    for category, lines in sections.items():
        st.markdown(f"### {(category[0] if isinstance(category, tuple) else category).upper()}")
        for line in lines:
            st.checkbox(line, value=False)

    # Show Recipe Guides on screen
    st.markdown("---")
    st.markdown("## 📋 Recipe Guides Preview")
    for recipe_name, (ingredients_list, method_text) in recipe_guides.items():
        st.markdown(f"### {recipe_name.upper()}")
        st.markdown("#### Ingredients:")
        for qty, unit, item in ingredients_list:
            qty_display = round(qty, 2)
            if float(qty_display).is_integer():
                qty_display = int(qty_display)
            st.markdown(f"- {qty_display} {unit} {item}")
        st.markdown("#### Method:")
        st.markdown(method_text)
        st.markdown("---")
    

    # Show Shopping List on screen
    st.markdown("## 🛒 Shopping List Preview")
    for category, lines in sections.items():
        st.markdown(f"### {category[0] if isinstance(category, tuple) else category}".upper())
        for line in lines:
            st.checkbox(line, value=False)

    # Show Recipe Guides on screen
    st.markdown("---")
    st.markdown("## 📋 Recipe Guides Preview")
    for recipe_name, (ingredients_list, method_text) in recipe_guides.items():
        st.markdown(f"### {recipe_name.upper()}")
        st.markdown("#### Ingredients:")
        for qty, unit, item in ingredients_list:
            qty_display = round(qty, 2)
            if qty_display.is_integer():
                qty_display = int(qty_display)
            st.markdown(f"- {qty_display} {unit} {item}")
        st.markdown("#### Method:")
        st.markdown(method_text)
        st.markdown("---")
    
        with open(shop_pdf, "rb") as f:
                st.download_button("📥 Download Shopping List PDF", f, "shopping_list.pdf")

        with open(recipe_pdf, "rb") as f:
                st.download_button("📥 Download Recipe Guides PDF", f, "recipe_guides.pdf")

except Exception as e:
    st.error(f"Error loading app: {e}")
