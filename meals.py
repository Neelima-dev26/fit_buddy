"""Meal planner: a menu of dishes described by their ingredients, filtered strictly by your restrictions.

Dishes are filtered by ingredient lists (never by a language model's guess). It is still only a guide:
always read labels, and see a doctor or dietitian for allergies or medical diets.
"""
import random
import re
from datetime import date

import recipes

MEALS_API = 2
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]

# ---------- ingredient lexicon: name -> (shopping category, attributes) ----------
INGR = {}


def _add(cat, attrs, *names):
    for n in names:
        INGR[n] = (cat, frozenset(attrs.split()))


_add("produce", "", "tomato", "spinach", "cucumber", "bell pepper", "broccoli", "cabbage", "zucchini", "peas", "corn",
     "mushrooms", "avocado", "banana", "apple", "berries", "mango", "dates", "lemon", "mint", "cilantro", "spring onion",
     "mixed vegetables", "salad greens", "sprouts", "green chili", "curry leaves", "coconut")
_add("produce", "", "plantain", "pineapple", "papaya", "pomegranate", "basil", "bok choy", "seaweed", "olives")
_add("produce", "fish", "kimchi")
_add("produce", "root", "cassava")
_add("grains & bread", "", "polenta", "cornmeal")
_add("grains & bread", "gluten", "bulgur", "farro", "injera")
_add("dairy & eggs", "dairy", "ricotta")
_add("pantry", "sesame", "sesame seeds")
_add("pantry", "tree_nut", "pistachios")
_add("produce", "root", "onion", "garlic", "potato", "sweet potato", "carrot", "ginger")
_add("protein", "meat", "chicken")
_add("protein", "fish", "salmon", "tuna", "white fish")
_add("protein", "shellfish", "shrimp")
_add("protein", "soy", "tofu", "tempeh", "edamame")
_add("protein", "", "dal", "moong dal", "lentils", "chickpeas", "kidney beans", "black beans", "white beans", "falafel", "makhana")
_add("protein", "sesame", "hummus")
_add("dairy & eggs", "egg", "egg")
_add("dairy & eggs", "dairy", "milk", "yogurt", "curd", "paneer", "cheese", "cottage cheese", "ghee")
_add("dairy & eggs", "soy", "soy milk")
_add("dairy & eggs", "", "coconut milk")
_add("grains & bread", "", "ragi", "besan", "millet")
_add("protein", "meat", "turkey")
_add("produce", "", "eggplant", "okra", "pumpkin", "kale")
_add("pantry", "honey", "honey")
_add("grains & bread", "", "rice", "brown rice", "quinoa", "poha", "idli", "dosa", "corn tortilla", "rice noodles")
_add("grains & bread", "gluten", "oats", "semolina", "whole-wheat bread", "roti", "whole-wheat pasta", "pita", "noodles",
     "wheat tortilla", "whole-grain crackers")
_add("pantry", "", "olive oil", "cooking oil", "chia seeds", "spices", "salsa")
_add("pantry", "soy gluten", "soy sauce")
_add("pantry", "soy", "miso")
_add("pantry", "sesame", "tahini")
_add("pantry", "peanut", "peanut butter", "peanuts")
_add("pantry", "tree_nut", "almonds", "walnuts")

# ---------- menu: (type, name, cuisine, minutes, ingredients, tags) ----------
_D = [
    ("breakfast", "Oatmeal with banana and almonds", "American", 10, "oats milk banana almonds", "quick"),
    ("breakfast", "Overnight oats with berries and chia", "American", 5, "oats yogurt berries|chia seeds", "quick batch"),
    ("breakfast", "Yogurt with berries and walnuts", "Mediterranean", 3, "yogurt berries walnuts", "quick protein"),
    ("breakfast", "Veggie omelette with whole-wheat toast", "American", 15, "egg spinach tomato onion whole-wheat bread|olive oil", "protein"),
    ("breakfast", "Peanut butter banana toast", "American", 5, "whole-wheat bread|peanut butter banana", "quick"),
    ("breakfast", "Idli with sambar", "Indian", 25, "idli dal mixed vegetables tomato", ""),
    ("breakfast", "Vegetable upma", "Indian", 20, "semolina carrot peas onion curry leaves|cooking oil", ""),
    ("breakfast", "Poha with peanuts and peas", "Indian", 15, "poha peanuts peas onion lemon", "quick"),
    ("breakfast", "Moong dal chilla with mint chutney", "Indian", 20, "moong dal onion tomato mint green chili", "protein"),
    ("breakfast", "Tofu scramble with spinach on toast", "American", 15, "tofu spinach tomato whole-wheat bread|olive oil", "protein quick"),
    ("breakfast", "Shakshuka with pita", "Middle Eastern", 25, "egg tomato bell pepper onion pita|olive oil", "protein"),
    ("breakfast", "Rice congee with egg and spring onion", "East Asian", 30, "rice egg ginger spring onion", ""),
    ("breakfast", "Chia pudding with mango and coconut milk", "Southeast Asian", 5, "chia seeds|coconut milk mango", "quick batch"),
    ("breakfast", "Avocado toast with a boiled egg", "American", 10, "whole-wheat bread avocado egg lemon", "protein quick"),
    ("breakfast", "Paneer bhurji with roti", "Indian", 20, "paneer onion tomato roti green chili", "protein"),
    ("breakfast", "Banana-spinach smoothie with soy milk and oats", "American", 5, "banana spinach soy milk|oats", "quick"),
    ("breakfast", "Eggs with black beans and corn tortillas", "Latin American", 20, "egg black beans tomato corn tortilla onion", "protein"),
    ("breakfast", "Dosa with coconut chutney", "Indian", 25, "dosa coconut green chili", ""),
    ("lunch", "Dal, brown rice, and cucumber salad", "Indian", 35, "dal brown rice cucumber tomato onion spices", "batch protein"),
    ("lunch", "Chickpea salad with whole-wheat pita", "Mediterranean", 15, "chickpeas cucumber tomato|olive oil lemon pita", "quick protein"),
    ("lunch", "Rajma with rice and salad", "Indian", 40, "kidney beans rice onion tomato garlic ginger spices", "batch protein"),
    ("lunch", "Chicken burrito bowl", "Latin American", 30, "chicken rice black beans corn tomato salsa", "protein batch"),
    ("lunch", "Black bean and corn burrito bowl", "Latin American", 25, "black beans rice corn tomato avocado salsa", "protein"),
    ("lunch", "Tuna and white bean salad", "Mediterranean", 10, "tuna white beans|olive oil tomato lemon", "quick protein"),
    ("lunch", "Lentil soup with whole-wheat bread", "Middle Eastern", 35, "lentils carrot onion garlic whole-wheat bread|olive oil", "batch protein"),
    ("lunch", "Quinoa vegetable bowl with tahini", "Middle Eastern", 25, "quinoa broccoli carrot chickpeas tahini lemon", "protein"),
    ("lunch", "Vegetable khichdi with curd", "Indian", 30, "rice dal mixed vegetables curd ghee", "batch"),
    ("lunch", "Hummus and vegetable wrap", "Middle Eastern", 10, "wheat tortilla hummus cucumber carrot salad greens", "quick"),
    ("lunch", "Tofu and vegetable rice bowl", "East Asian", 25, "tofu rice broccoli carrot soy sauce ginger", "protein"),
    ("lunch", "Paneer tikka salad", "Indian", 25, "paneer bell pepper onion yogurt salad greens lemon", "protein"),
    ("lunch", "Egg fried rice with vegetables", "East Asian", 20, "egg rice peas carrot soy sauce spring onion", "quick"),
    ("lunch", "Falafel wrap with salad", "Middle Eastern", 20, "falafel pita cucumber tomato tahini", ""),
    ("lunch", "Pasta salad with beans and vegetables", "Italian", 20, "whole-wheat pasta white beans tomato cucumber|olive oil spinach", "batch"),
    ("lunch", "Chicken and vegetable noodle soup", "Southeast Asian", 30, "chicken rice noodles carrot cabbage ginger cilantro", "protein"),
    ("lunch", "Sambar rice with a vegetable poriyal", "Indian", 35, "rice dal mixed vegetables tomato curry leaves", "batch"),
    ("dinner", "Chicken and vegetable stir-fry with rice", "East Asian", 25, "chicken broccoli bell pepper rice soy sauce garlic ginger", "protein"),
    ("dinner", "Baked salmon with roasted vegetables and potatoes", "Mediterranean", 35, "salmon broccoli potato|olive oil lemon", "protein"),
    ("dinner", "Chana masala with roti", "Indian", 40, "chickpeas tomato onion garlic ginger roti spices", "batch protein"),
    ("dinner", "Vegetable and bean chili", "American", 40, "kidney beans black beans tomato bell pepper onion corn", "batch protein"),
    ("dinner", "Whole-wheat pasta with tomato and vegetable sauce", "Italian", 25, "whole-wheat pasta tomato zucchini garlic|olive oil spinach", "quick"),
    ("dinner", "Lentil curry with brown rice", "Indian", 35, "dal brown rice spinach tomato onion spices", "batch protein"),
    ("dinner", "Tofu and vegetable stir-fry with noodles", "East Asian", 25, "tofu noodles cabbage carrot soy sauce garlic", "protein"),
    ("dinner", "Egg curry with rice", "Indian", 35, "egg tomato onion rice spices", "protein"),
    ("dinner", "Grilled fish with quinoa and cucumber salad", "Mediterranean", 25, "white fish quinoa cucumber lemon|olive oil", "protein"),
    ("dinner", "Shrimp and vegetable stir-fry with rice", "Southeast Asian", 25, "shrimp bell pepper broccoli rice garlic ginger", "protein quick"),
    ("dinner", "Baked chicken with tomatoes and zucchini", "Mediterranean", 35, "chicken tomato zucchini|olive oil garlic", "protein"),
    ("dinner", "Palak paneer with roti", "Indian", 35, "spinach paneer onion roti garlic", "protein"),
    ("dinner", "Vegetable pulao with raita", "Indian", 35, "rice peas carrot onion yogurt cucumber", ""),
    ("dinner", "Miso soup with tofu and a rice bowl", "East Asian", 20, "miso tofu spinach rice spring onion", "quick"),
    ("dinner", "Black bean tacos on corn tortillas", "Latin American", 20, "black beans corn tortilla cabbage tomato avocado lemon", "quick protein"),
    ("dinner", "Peanut and sweet potato stew with brown rice", "African / Caribbean", 40, "peanuts sweet potato tomato spinach brown rice onion ginger", "batch"),
    ("dinner", "Lentil and vegetable stew", "African / Caribbean", 40, "lentils tomato onion garlic carrot spices", "batch protein"),
    ("dinner", "Rice and peas with grilled fish and salad", "African / Caribbean", 35, "rice kidney beans|coconut milk white fish tomato salad greens", "protein"),
    ("dinner", "Thai-style vegetable curry with tofu and rice", "Southeast Asian", 30, "tofu|coconut milk bell pepper broccoli rice ginger spices", "protein"),
    ("dinner", "Lemon herb chicken with sweet potato and salad", "American", 35, "chicken sweet potato lemon salad greens|olive oil", "protein"),
    ("dinner", "Minestrone soup with whole-wheat bread", "Italian", 40, "white beans carrot tomato zucchini whole-wheat pasta onion whole-wheat bread", "batch"),
    ("dinner", "Stuffed bell peppers with rice and beans", "Latin American", 40, "bell pepper rice black beans tomato cheese onion", ""),
    ("lunch", "Moong dal soup with rice", "Indian", 25, "moong dal rice spices lemon", "protein quick"),
    ("lunch", "Chickpea and tomato rice bowl", "Mediterranean", 25, "chickpeas tomato rice cucumber lemon|olive oil", "protein"),
    ("dinner", "Moong dal khichdi with ghee", "Indian", 30, "rice moong dal ghee mixed vegetables", "protein"),
    ("dinner", "Paneer and capsicum curry with roti", "Indian", 30, "paneer bell pepper tomato roti spices", "protein"),
    ("dinner", "Dal with rice and cucumber raita", "Indian", 30, "dal rice cucumber yogurt spices", "protein"),
    ("dinner", "Vegetable coconut curry with rice", "Southeast Asian", 30, "coconut milk mixed vegetables bell pepper broccoli rice spices", ""),
    ("dinner", "Quinoa, chickpea, and cucumber bowl", "Mediterranean", 20, "quinoa chickpeas cucumber tomato lemon|olive oil", "protein quick"),
    ("dinner", "Rice with black beans and avocado", "Latin American", 25, "rice black beans avocado tomato lemon corn", "protein quick"),
    ("snack", "Apple slices with peanut butter", "American", 3, "apple|peanut butter", "quick"),
    ("snack", "Yogurt with berries", "American", 2, "yogurt berries", "quick protein"),
    ("snack", "Hummus with carrot and cucumber sticks", "Middle Eastern", 5, "hummus carrot cucumber", "quick"),
    ("snack", "Roasted chickpeas", "Indian", 5, "chickpeas spices", "batch"),
    ("snack", "Boiled egg with an apple", "Any", 10, "egg apple", "protein"),
    ("snack", "Almonds and dates", "Middle Eastern", 1, "almonds dates", "quick"),
    ("snack", "Fruit chaat", "Indian", 5, "apple banana lemon spices", "quick"),
    ("snack", "Sprouts chaat", "Indian", 10, "sprouts onion tomato lemon cilantro", "protein"),
    ("snack", "Edamame with sea salt", "East Asian", 5, "edamame", "protein quick"),
    ("snack", "Whole-grain crackers with cheese", "Any", 3, "whole-grain crackers cheese", "quick"),
    ("snack", "Cottage cheese with berries", "American", 3, "cottage cheese berries", "protein quick"),
    ("snack", "Roasted makhana (fox nuts)", "Indian", 5, "makhana spices", "quick"),
    ("snack", "Cucumber and carrot sticks with a yogurt dip", "Mediterranean", 5, "cucumber yogurt carrot lemon", "quick"),
    ("breakfast", "Besan chilla with vegetables", "Indian", 15, "besan onion tomato green chili cooking oil", "protein quick"),
    ("breakfast", "Ragi porridge with banana", "Indian", 15, "ragi milk banana", ""),
    ("breakfast", "Masala omelette with roti", "Indian", 15, "egg onion tomato green chili roti", "protein"),
    ("breakfast", "Vegetable oats upma", "Indian", 15, "oats carrot peas onion curry leaves cooking oil", "quick"),
    ("breakfast", "Yogurt with oats and berries", "Mediterranean", 5, "yogurt oats berries", "quick"),
    ("breakfast", "Whole-grain toast with cottage cheese and tomato", "Italian", 5, "whole-wheat bread cottage cheese tomato olive oil", "quick protein"),
    ("breakfast", "Berry smoothie bowl with chia", "American", 5, "berries banana yogurt chia seeds", "quick"),
    ("breakfast", "Sweet potato and black bean breakfast burrito", "Latin American", 25, "sweet potato black beans wheat tortilla avocado", "protein"),
    ("breakfast", "Pesarattu (green gram dosa)", "Indian", 20, "moong dal ginger green chili onion", "protein"),
    ("breakfast", "Apple cinnamon oatmeal", "American", 10, "oats apple milk spices", "quick"),
    ("breakfast", "Oat and banana pancakes", "American", 15, "oats banana egg milk", ""),
    ("breakfast", "Peanut butter overnight oats", "American", 5, "oats milk peanut butter banana", "quick batch"),
    ("breakfast", "Spinach and cheese egg muffins", "American", 25, "egg spinach cheese bell pepper", "batch protein"),
    ("breakfast", "Honey yogurt with walnuts and mango", "Middle Eastern", 3, "yogurt honey walnuts mango", "quick"),
    ("lunch", "Chicken tikka wrap with salad", "Indian", 20, "chicken yogurt wheat tortilla cucumber onion salad greens", "protein"),
    ("lunch", "Vegetable biryani with raita", "Indian", 45, "rice mixed vegetables yogurt onion spices ghee", "batch"),
    ("lunch", "Curd rice with cucumber", "Indian", 10, "rice curd cucumber curry leaves green chili", "quick"),
    ("lunch", "Lemon rice with peanuts", "Indian", 20, "rice peanuts lemon curry leaves green chili", ""),
    ("lunch", "Greek salad with chickpeas and feta", "Mediterranean", 15, "cucumber tomato chickpeas cheese olive oil lemon", "quick protein"),
    ("lunch", "Salmon rice bowl with cucumber and avocado", "East Asian", 20, "salmon rice cucumber avocado soy sauce", "protein"),
    ("lunch", "Tofu pad thai-style noodles", "Southeast Asian", 25, "tofu rice noodles peanuts sprouts lemon", "protein"),
    ("lunch", "Tofu rice paper rolls with peanut dip", "Southeast Asian", 25, "tofu rice noodles cucumber carrot mint peanut butter", ""),
    ("lunch", "Caprese sandwich on whole-wheat bread", "Italian", 10, "whole-wheat bread tomato cheese salad greens olive oil", "quick"),
    ("lunch", "Turkey and avocado wrap", "American", 10, "turkey avocado wheat tortilla salad greens tomato", "quick protein"),
    ("lunch", "Quinoa tabbouleh with chickpeas", "Middle Eastern", 20, "quinoa tomato cucumber mint lemon olive oil chickpeas", "protein batch"),
    ("lunch", "Cabbage and lentil soup with bread", "Middle Eastern", 35, "lentils cabbage carrot onion whole-wheat bread", "batch protein"),
    ("lunch", "Jollof-style rice with beans", "African / Caribbean", 35, "rice tomato bell pepper onion kidney beans spices", "batch"),
    ("lunch", "Sweet corn and bean salad with lime", "Latin American", 15, "corn black beans tomato cilantro lemon avocado", "quick"),
    ("dinner", "Chicken biryani with raita", "Indian", 50, "chicken rice yogurt onion spices ghee cucumber", "protein batch"),
    ("dinner", "Chicken curry with rice", "Indian", 40, "chicken tomato onion garlic ginger rice spices", "protein"),
    ("dinner", "Fish curry with rice", "Indian", 35, "white fish tomato onion coconut milk rice spices", "protein"),
    ("dinner", "Mixed vegetable curry with roti", "Indian", 35, "mixed vegetables tomato onion roti spices", ""),
    ("dinner", "Baingan bharta with roti", "Indian", 35, "eggplant tomato onion roti garlic", ""),
    ("dinner", "Bhindi masala with dal and roti", "Indian", 40, "okra onion tomato dal roti", "protein"),
    ("dinner", "Tandoori-style chicken with rice and salad", "Indian", 40, "chicken yogurt lemon salad greens rice spices", "protein"),
    ("dinner", "Turkey meatballs with whole-wheat pasta", "Italian", 35, "turkey whole-wheat pasta tomato garlic onion", "protein"),
    ("dinner", "Eggplant and chickpea stew", "Middle Eastern", 40, "eggplant chickpeas tomato onion garlic olive oil", "batch protein"),
    ("dinner", "Mushroom and spinach whole-wheat pasta", "Italian", 25, "mushrooms spinach whole-wheat pasta garlic olive oil", "quick"),
    ("dinner", "Teriyaki-style salmon with rice and broccoli", "East Asian", 30, "salmon soy sauce rice broccoli ginger", "protein"),
    ("dinner", "Bibimbap-style rice bowl with egg", "East Asian", 35, "rice egg spinach carrot mushrooms soy sauce", "protein"),
    ("dinner", "Chickpea and coconut curry with rice", "Indian", 30, "chickpeas coconut milk tomato rice spices", "batch protein"),
    ("dinner", "Jerk-style chicken with rice and peas", "African / Caribbean", 40, "chicken rice kidney beans coconut milk spices", "protein"),
    ("dinner", "Bean and veggie quesadillas", "Latin American", 20, "wheat tortilla black beans cheese bell pepper", "quick"),
    ("dinner", "Shrimp tacos with cabbage slaw", "Latin American", 25, "shrimp corn tortilla cabbage lemon avocado", "protein quick"),
    ("dinner", "Pumpkin and lentil soup with bread", "Mediterranean", 35, "pumpkin lentils onion garlic whole-wheat bread", "batch"),
    ("dinner", "Kale and white bean stew", "Italian", 35, "kale white beans tomato garlic onion olive oil", "batch protein"),
    ("snack", "Guacamole with veggie sticks", "Latin American", 10, "avocado lemon cucumber carrot tomato", "quick"),
    ("snack", "Banana with peanut butter", "American", 2, "banana peanut butter", "quick"),
    ("snack", "Roasted sweet potato wedges", "American", 30, "sweet potato olive oil spices", "batch"),
    ("snack", "Stovetop popcorn", "American", 8, "corn cooking oil", "quick"),
    ("snack", "Berry and soy milk smoothie", "American", 5, "berries banana soy milk", "quick"),
    ("snack", "Boiled corn chaat", "Indian", 10, "corn lemon spices onion cilantro", "quick"),
    ("snack", "Greek yogurt with honey and walnuts", "Mediterranean", 3, "yogurt honey walnuts", "quick protein"),
    ("snack", "Roasted peanuts and fruit", "Indian", 3, "peanuts apple", "quick"),
    ("snack", "Dates stuffed with almonds", "Middle Eastern", 5, "dates almonds", "quick"),
    ("snack", "Mini bean and cheese quesadilla", "Latin American", 10, "wheat tortilla black beans cheese", "quick protein"),
    ('breakfast', 'Japanese-style rice porridge with vegetables', 'East Asian', 25, 'rice mixed vegetables ginger spring onion', ''),
    ('breakfast', 'Tofu and spinach miso breakfast soup', 'East Asian', 10, 'miso tofu spinach spring onion', 'quick protein'),
    ('breakfast', 'Sesame rice balls with seaweed', 'East Asian', 15, 'rice seaweed sesame seeds', 'quick'),
    ('breakfast', 'Soy milk oat porridge with banana and berries', 'East Asian', 10, 'oats soy milk banana berries', 'quick'),
    ('breakfast', 'Egg and tomato stir-fry with rice', 'East Asian', 15, 'egg tomato rice spring onion', 'protein quick'),
    ('lunch', 'Cold sesame noodle salad', 'East Asian', 20, 'noodles cucumber carrot sesame seeds soy sauce', ''),
    ('lunch', 'Chicken noodle soup with bok choy', 'East Asian', 30, 'chicken noodles bok choy ginger soy sauce', 'protein'),
    ('lunch', 'Vegetable sushi-style rice bowl', 'East Asian', 20, 'rice cucumber avocado carrot seaweed soy sauce', ''),
    ('dinner', 'Mapo-style tofu with mushrooms and rice', 'East Asian', 25, 'tofu mushrooms rice garlic ginger soy sauce', 'protein'),
    ('dinner', 'Kimchi fried rice with vegetables', 'East Asian', 20, 'kimchi rice peas carrot cooking oil', ''),
    ('snack', 'Edamame with sesame seeds', 'East Asian', 5, 'edamame sesame seeds', 'protein quick'),
    ('snack', 'Cucumber sesame salad', 'East Asian', 5, 'cucumber sesame seeds soy sauce', 'quick'),
    ('snack', 'Crispy tofu bites with soy dip', 'East Asian', 15, 'tofu soy sauce', 'protein'),
    ('snack', 'Steamed sweet potato', 'East Asian', 20, 'sweet potato', 'batch'),
    ('snack', 'Miso soup cup with tofu', 'East Asian', 5, 'miso tofu spring onion', 'quick'),
    ('breakfast', 'Warm chickpea and tomato breakfast bowl', 'Middle Eastern', 15, 'chickpeas tomato olive oil lemon pita', 'protein quick'),
    ('breakfast', 'Yogurt with cucumber, mint, and olive oil', 'Middle Eastern', 5, 'yogurt cucumber olive oil mint pita', 'quick'),
    ('breakfast', 'Date and walnut oat bowl', 'Middle Eastern', 10, 'oats dates walnuts milk', 'quick'),
    ('dinner', 'Chicken shawarma-style plate with rice and salad', 'Middle Eastern', 35, 'chicken yogurt rice salad greens tomato cucumber spices', 'protein'),
    ('dinner', 'Lentil and rice mujadara-style bowl', 'Middle Eastern', 40, 'lentils rice onion olive oil yogurt', 'batch protein'),
    ('dinner', 'Stuffed eggplant with chickpeas and tomato', 'Middle Eastern', 40, 'eggplant chickpeas tomato onion olive oil', 'protein'),
    ('dinner', 'Grilled fish with bulgur and tomato salad', 'Middle Eastern', 30, 'white fish bulgur tomato cucumber lemon olive oil', 'protein'),
    ('snack', 'Olives and cucumber with pita', 'Middle Eastern', 5, 'olives cucumber pita', 'quick'),
    ('snack', 'Pistachio and pomegranate yogurt', 'Middle Eastern', 5, 'yogurt pistachios pomegranate', 'quick protein'),
    ('breakfast', 'Plantain and black bean breakfast plate', 'African / Caribbean', 25, 'plantain black beans tomato onion', 'protein'),
    ('breakfast', 'Cornmeal porridge with banana', 'African / Caribbean', 15, 'cornmeal milk banana spices', ''),
    ('breakfast', 'Mango and coconut yogurt bowl', 'African / Caribbean', 5, 'yogurt mango coconut', 'quick'),
    ('breakfast', 'Spinach and tomato egg scramble', 'African / Caribbean', 15, 'egg spinach tomato onion', 'protein quick'),
    ('breakfast', 'Millet porridge with banana and coconut milk', 'African / Caribbean', 20, 'millet coconut milk banana', ''),
    ('lunch', 'Rice and beans salad with plantain', 'African / Caribbean', 30, 'rice kidney beans plantain tomato', 'batch'),
    ('lunch', 'Lentil stew wrap on injera', 'African / Caribbean', 30, 'lentils injera tomato onion garlic spices', 'protein'),
    ('lunch', 'Peanut chicken stew with rice', 'African / Caribbean', 40, 'chicken peanut butter tomato rice onion', 'protein'),
    ('lunch', 'Caribbean pumpkin soup with bread', 'African / Caribbean', 30, 'pumpkin coconut milk onion whole-wheat bread', 'batch'),
    ('dinner', 'Curried chickpeas with sweet potato', 'African / Caribbean', 35, 'chickpeas sweet potato coconut milk spices tomato', 'batch protein'),
    ('snack', 'Baked plantain chips', 'African / Caribbean', 25, 'plantain olive oil', 'batch'),
    ('snack', 'Mango and pineapple cup', 'African / Caribbean', 5, 'mango pineapple lemon', 'quick'),
    ('snack', 'Roasted cassava wedges', 'African / Caribbean', 30, 'cassava olive oil spices', 'batch'),
    ('snack', 'Roasted peanuts and papaya', 'African / Caribbean', 3, 'peanuts papaya', 'quick'),
    ('snack', 'Coconut yogurt with pineapple', 'African / Caribbean', 3, 'yogurt coconut pineapple', 'quick'),
    ('breakfast', 'Ricotta toast with berries and honey', 'Italian', 5, 'whole-wheat bread ricotta berries honey', 'quick'),
    ('breakfast', 'Tomato and basil scrambled eggs on toast', 'Italian', 10, 'egg tomato basil whole-wheat bread', 'protein quick'),
    ('breakfast', 'Polenta porridge with berries', 'Italian', 15, 'polenta milk berries', ''),
    ('breakfast', 'Vegetable frittata slice with bread', 'Italian', 25, 'egg zucchini spinach cheese whole-wheat bread', 'batch protein'),
    ('lunch', 'Tuscan white bean and kale soup', 'Italian', 35, 'white beans kale carrot onion olive oil', 'batch protein'),
    ('lunch', 'Panzanella-style tomato and bread salad', 'Italian', 15, 'whole-wheat bread tomato cucumber olive oil basil', 'quick'),
    ('lunch', 'Farro salad with chickpeas and tomatoes', 'Italian', 25, 'farro chickpeas tomato cucumber olive oil', 'protein'),
    ('snack', 'Tomato and basil crostini', 'Italian', 10, 'whole-wheat bread tomato basil olive oil', 'quick'),
    ('snack', 'Olives and cheese cubes', 'Italian', 3, 'olives cheese', 'quick'),
    ('snack', 'Apple with walnuts and cheese', 'Italian', 3, 'apple walnuts cheese', 'quick'),
    ('snack', 'Cucumber and mozzarella bites', 'Italian', 5, 'cucumber cheese basil', 'quick'),
    ('snack', 'Berry yogurt with pistachios', 'Italian', 3, 'yogurt berries pistachios', 'quick protein'),
    ('breakfast', 'Rice noodle soup with tofu and greens', 'Southeast Asian', 20, 'rice noodles tofu bok choy ginger', 'protein'),
    ('breakfast', 'Coconut rice porridge with mango', 'Southeast Asian', 25, 'rice coconut milk mango', ''),
    ('breakfast', 'Banana and coconut oat bowl', 'Southeast Asian', 10, 'oats coconut milk banana coconut', 'quick'),
    ('breakfast', 'Thai-style egg and vegetable fried rice', 'Southeast Asian', 15, 'egg rice peas carrot soy sauce', 'protein quick'),
    ('breakfast', 'Mango sticky rice (lighter version)', 'Southeast Asian', 25, 'rice mango coconut milk', ''),
    ('lunch', 'Vietnamese-style chicken salad with herbs and peanuts', 'Southeast Asian', 25, 'chicken cabbage carrot mint peanuts lemon', 'protein'),
    ('lunch', 'Tofu and peanut noodle bowl', 'Southeast Asian', 20, 'tofu rice noodles cucumber peanut butter', 'protein'),
    ('dinner', 'Thai basil chicken with rice', 'Southeast Asian', 25, 'chicken basil green chili garlic rice', 'protein'),
    ('dinner', 'Coconut fish curry with rice', 'Southeast Asian', 30, 'white fish coconut milk bell pepper rice ginger spices', 'protein'),
    ('snack', 'Fresh fruit with lemon and chili', 'Southeast Asian', 5, 'pineapple mango lemon', 'quick'),
    ('snack', 'Peanut tofu skewers', 'Southeast Asian', 20, 'tofu peanut butter', 'protein'),
    ('snack', 'Cucumber and mint salad', 'Southeast Asian', 5, 'cucumber mint lemon', 'quick'),
    ('snack', 'Steamed corn on the cob', 'Southeast Asian', 15, 'corn', 'quick'),
    ('snack', 'Fresh vegetable rice paper rolls', 'Southeast Asian', 15, 'rice noodles carrot cucumber mint', ''),
    ('breakfast', 'Egg and black bean tacos', 'Latin American', 15, 'egg black beans corn tortilla salsa', 'protein'),
    ('breakfast', 'Papaya and pineapple yogurt bowl', 'Latin American', 5, 'papaya pineapple yogurt lemon', 'quick'),
    ('breakfast', 'Cinnamon banana oatmeal (avena)', 'Latin American', 10, 'oats milk banana spices', 'quick'),
    ('lunch', 'Chicken and avocado rice bowl', 'Latin American', 25, 'chicken rice avocado corn salsa', 'protein'),
    ('lunch', 'Cuban-style black beans and rice', 'Latin American', 35, 'black beans rice onion bell pepper spices', 'batch protein'),
    ('snack', 'Corn and bean salsa with veggie sticks', 'Latin American', 10, 'corn black beans tomato cilantro lemon cucumber', 'quick'),
    ('snack', 'Mango with lime', 'Latin American', 3, 'mango lemon', 'quick'),
    ('snack', 'Baked tortilla chips with salsa', 'Latin American', 10, 'corn tortilla salsa', 'quick'),
    ('breakfast', 'Whole-grain toast with hummus and tomato', 'Mediterranean', 5, 'whole-wheat bread hummus tomato cucumber', 'quick'),
    ('breakfast', 'Spinach and feta omelette', 'Mediterranean', 15, 'egg spinach cheese olive oil', 'protein'),
    ('breakfast', 'Oats with apple and almonds', 'Mediterranean', 10, 'oats milk apple almonds', 'quick'),
    ('lunch', 'Lentil and vegetable salad with feta', 'Mediterranean', 20, 'lentils cucumber tomato cheese olive oil lemon', 'protein'),
    ('snack', 'Olives and whole-grain bread', 'Mediterranean', 3, 'olives whole-wheat bread', 'quick'),
    ('snack', 'Hummus with whole-wheat pita', 'Mediterranean', 5, 'hummus pita', 'quick'),
    ('snack', 'Tomato and cucumber salad with olive oil', 'Mediterranean', 5, 'tomato cucumber olive oil', 'quick'),
    ('lunch', 'Black bean veggie burger on whole-wheat bread', 'American', 25, 'black beans whole-wheat bread salad greens tomato', 'protein'),
    ('lunch', 'Chicken and veggie salad bowl', 'American', 15, 'chicken salad greens tomato cucumber olive oil', 'protein quick'),
    ('lunch', 'Tuna salad sandwich', 'American', 10, 'tuna whole-wheat bread salad greens tomato yogurt', 'protein quick'),
    ('lunch', 'Lentil vegetable soup with crackers', 'American', 30, 'lentils carrot onion whole-grain crackers', 'batch protein'),
    ('dinner', 'Turkey and bean chili', 'American', 40, 'turkey kidney beans tomato onion bell pepper', 'batch protein'),
    ('dinner', 'Baked salmon with sweet potato and broccoli', 'American', 35, 'salmon sweet potato broccoli olive oil lemon', 'protein'),
    ('dinner', 'Tofu and vegetable sheet-pan dinner', 'American', 35, 'tofu bell pepper broccoli sweet potato olive oil', 'protein'),
]


def _parse_ingredients(spec):
    """'a b|multi word c' -> longest-match split against the lexicon (names can contain spaces)."""
    words = spec.replace("|", " ").split()
    out, i = [], 0
    while i < len(words):
        for n in range(4, 0, -1):
            cand = " ".join(words[i:i + n])
            if cand in INGR:
                out.append(cand)
                i += n
                break
        else:
            raise ValueError(f"unknown ingredient near '{words[i]}' in: {spec}")
    return out


DISHES = []
for _t, _name, _cuisine, _mins, _spec, _tags in _D:
    _ings = _parse_ingredients(_spec)
    _attrs = frozenset().union(*(INGR[i][1] for i in _ings))
    DISHES.append({"type": _t, "name": _name, "cuisine": _cuisine, "minutes": _mins, "ingredients": _ings,
                   "tags": set(_tags.split()), "attrs": _attrs, "method": recipes.METHODS.get(_name, "")})


# ---------- filtering ----------
def excluded_attrs(p):
    """Ingredient attributes a profile must avoid. Diet words and allergens both end up here."""
    ex, diets = set(p["allergens"]), set(p["diets"])
    if "vegan" in diets:
        ex |= {"meat", "fish", "shellfish", "egg", "dairy", "honey"}
    elif "vegetarian" in diets:
        ex |= {"meat", "fish", "shellfish"}
    elif "pescatarian" in diets:
        ex |= {"meat"}
    if "jain" in diets:
        ex |= {"meat", "fish", "shellfish", "egg", "root"}
    if "halal" in diets:
        ex |= {"pork"}
    if "kosher" in diets:
        ex |= {"pork", "shellfish"}
    return ex


def eligible(p):
    ex, avoid = excluded_attrs(p), p["avoid"]
    out = []
    for d in DISHES:
        if d["attrs"] & ex:
            continue
        text = d["name"].lower() + " " + " ".join(d["ingredients"])
        if any(w in text for w in avoid):
            continue
        out.append(d)
    return out


def notes_for(p):
    """Honest notes about what the filter can and cannot promise."""
    out = []
    if "kosher" in p["diets"]:
        out.append("Kosher: I only exclude pork and shellfish. I cannot check kosher preparation.")
    if "halal" in p["diets"]:
        out.append("Halal: I exclude pork, but I cannot check how meat was sourced or prepared.")
    if "jain" in p["diets"]:
        out.append("Jain: I exclude meat, fish, eggs, and root vegetables such as onion, garlic, potato, and carrot.")
    if "vegetarian" in p["diets"]:
        out.append("Vegetarian dishes can include eggs and dairy. Say vegan, or no eggs or dairy, to exclude them.")
    if "gluten" in p["allergens"]:
        out.append("Gluten-free: oats are excluded because they are often cross-contaminated. Check labels on packaged foods.")
    for w in p["avoid"]:
        if not any(w in (d["name"].lower() + " " + " ".join(d["ingredients"])) for d in DISHES):
            out.append(f"No dish on my menu contains \"{w}\", so nothing was removed for it.")
    if p["restrictions_unmatched"]:
        out.append(f"I did not recognize \"{p['restrictions_unmatched']}\", so no filtering was applied for it.")
    out.append("I filter dishes by their ingredient lists, but I cannot guarantee allergen safety. Always check labels, and ask a "
               "doctor or dietitian about allergies and medical diets.")
    return out


# ---------- plan ----------
def build_plan(p, seed=0, today=None):
    """A week of meals. Dishes from your chosen cuisines are used first (each at most once), then other cuisines fill the gaps."""
    today = today or date.today()
    pool = eligible(p)
    warnings = []
    prefs = [c for c in p["cuisines"] if c != "Any"]
    plan_days = [{"day": d} for d in DAY_NAMES]
    rng = random.Random(f"{p['meal_sig']}-{seed}")
    sizes, matched, total = {}, 0, 0
    for mtype in MEAL_TYPES:
        of_type = [d for d in pool if d["type"] == mtype]
        sizes[mtype] = len(of_type)
        if not of_type:
            warnings.append(f"No {mtype} dishes fit your restrictions, so that meal is left open.")
            for day in plan_days:
                day[mtype] = None
            continue
        liked = [d for d in of_type if d["cuisine"] in prefs or d["cuisine"] == "Any"] if prefs else of_type
        others = [d for d in of_type if d not in liked]
        rng.shuffle(liked)
        rng.shuffle(others)
        if prefs and len(liked) < 7 and others:
            warnings.append(f"Only {len(liked)} {mtype} dishes match your cuisines and restrictions, so the rest come from other cuisines.")
        order = liked[:7] + others                      # your cuisines first, others only to fill the week
        picked = [order[i % len(order)] for i in range(7)] if len(order) < 7 else order[:7]
        rng.shuffle(picked)                              # spread favorites across the week
        for i in range(1, 7):                            # never the same dish two days in a row
            if picked[i] is picked[i - 1]:
                j = next((k for k in range(i + 1, 7) if picked[k] is not picked[i]), None)
                if j is not None:
                    picked[i], picked[j] = picked[j], picked[i]
        for day, dish in zip(plan_days, picked):
            day[mtype] = dish
            total += 1
            matched += 1 if (not prefs or dish["cuisine"] in prefs or dish["cuisine"] == "Any") else 0
    for day in plan_days:   # make sure lunch or dinner is protein-rich when possible
        l, d = day.get("lunch"), day.get("dinner")
        if l and d and "protein" not in l["tags"] and "protein" not in d["tags"]:
            alts = [x for x in pool if x["type"] == "dinner" and "protein" in x["tags"]
                    and (not prefs or x["cuisine"] in prefs or x["cuisine"] == "Any")]
            fresh = [x for x in alts if all(x is not other.get("dinner") for other in plan_days)]
            if fresh or alts:
                day["dinner"] = rng.choice(fresh or alts)
    if len(pool) == 0:
        warnings.append("No dishes fit these restrictions. Please check your entries or ask a dietitian.")
    if prefs:
        matched = sum(1 for day in plan_days for t in MEAL_TYPES if day.get(t) and (day[t]["cuisine"] in prefs or day[t]["cuisine"] == "Any"))
        total = sum(1 for day in plan_days for t in MEAL_TYPES if day.get(t))
    return {"created": today.isoformat(), "seed": seed, "meal_sig": p["meal_sig"], "days": plan_days,
            "warnings": warnings, "notes": notes_for(p), "sizes": sizes, "cuisine_match": (matched, total) if prefs else None}


def shopping_list(plan):
    """{category: [(ingredient, number of meals)]} for the whole week."""
    counts = {}
    for day in plan["days"]:
        for t in MEAL_TYPES:
            d = day.get(t)
            if d:
                for ing in set(d["ingredients"]):
                    counts[ing] = counts.get(ing, 0) + 1
    grouped = {}
    for ing, n in sorted(counts.items()):
        grouped.setdefault(INGR[ing][0], []).append((ing, n))
    return grouped


ICONS = {"breakfast": "\U0001F373", "lunch": "\U0001F957", "dinner": "\U0001F35B", "snack": "\U0001F34E"}


def day_markdown(plan, idx):
    """Compact view of one day: icon, meal, dish, and time."""
    day = plan["days"][idx]
    lines = []
    for t in MEAL_TYPES:
        d = day.get(t)
        lines.append(f"{ICONS[t]} **{t.capitalize()}** - " + (f"{d['name']} ({d['minutes']} min)" if d else "nothing fits your restrictions"))
    return "\n\n".join(lines)


def rest_of_day(plan, weekday, hour):
    """The planned meals still ahead today, given the time of day (a meal just logged counts as eaten)."""
    if hour < 11:
        types = ["lunch", "dinner", "snack"]
    elif hour < 15:
        types = ["dinner", "snack"]
    elif hour < 18:
        types = ["dinner"]
    elif hour < 21:
        types = ["snack"]
    else:
        types = []
    day = plan["days"][weekday]
    return [(t, day[t]) for t in types if day.get(t)]


def find_dish(query, p=None):
    """Best-matching dish for 'recipe for chicken biryani'. Returns (dish, allowed_for_profile) or (None, True)."""
    words = [w for w in re.findall(r"[a-z]+", (query or "").lower())
             if w not in {"recipe", "recipes", "for", "how", "to", "make", "cook", "prepare", "do", "i", "a", "the", "with", "can", "show", "me", "of", "and"}]
    if not words:
        return None, True
    best, score = None, 0
    for d in DISHES:
        text = d["name"].lower() + " " + " ".join(d["ingredients"])
        sc = sum(3 if w in d["name"].lower() else 1 for w in words if w in text or w.rstrip("s") in text)
        if sc > score:
            best, score = d, sc
    if not best or score < max(2, len(words)):
        return None, True
    return best, (best in eligible(p)) if p else True


def recipe_markdown(d, allowed=True):
    parts = [f"**{d['name']}** - {d['cuisine']}, about {d['minutes']} min",
             "**You need:** " + ", ".join(i for i in d["ingredients"] if i != "spices") + (" and spices" if "spices" in d["ingredients"] else ""),
             "**How:** " + (d["method"] or "Cook the main ingredients, combine, and season to taste.")]
    if not allowed:
        parts.append("Note: this dish contains something you excluded in your preferences.")
    return "\n\n".join(parts)


def suggest(p, meal_type=None, n=5, seen=None, seed=0):
    """Several dishes from the whole menu that fit the profile, avoiding ones already shown."""
    seen = set(seen or [])
    pool = eligible(p)
    prefs = [c for c in p["cuisines"] if c != "Any"]
    if prefs:
        liked = [d for d in pool if d["cuisine"] in prefs or d["cuisine"] == "Any"]
        pool = liked if len(liked) >= n else pool
    rng = random.Random(f"{p['meal_sig']}-{seed}-{len(seen)}")
    types = [meal_type] if meal_type else ["breakfast", "lunch", "dinner", "dinner", "snack"]
    out, used = [], set()
    for t in (types * n)[:n] if meal_type else types[:n]:
        cands = [d for d in pool if d["type"] == t and d["name"] not in used and d["name"] not in seen]
        if not cands:
            cands = [d for d in pool if d["type"] == t and d["name"] not in used]
        if cands:
            d = rng.choice(cands)
            out.append(d)
            used.add(d["name"])
    return out


def suggestions_markdown(dishes):
    return "\n\n".join(f"{ICONS[d['type']]} **{d['name']}** - {d['minutes']} min, {d['cuisine']}" for d in dishes)


_GRAINS = {"rice", "brown rice", "quinoa", "millet"}
_LEGUMES = {"dal", "moong dal", "lentils", "chickpeas", "kidney beans", "black beans", "white beans"}
_FRUIT = {"banana", "apple", "berries", "mango", "dates", "lemon", "avocado", "coconut"}


def prep_plan(plan):
    """A batch-cooking checklist for the week, built from the planned dishes."""
    counts, dishes = {}, []
    for day in plan["days"]:
        for t in MEAL_TYPES:
            d = day.get(t)
            if d:
                dishes.append(d)
                for i in set(d["ingredients"]):
                    counts[i] = counts.get(i, 0) + 1
    tasks, minutes = [], 0
    grains = legumes = 0
    for ing, n in sorted(counts.items(), key=lambda x: -x[1]):
        if ing in _GRAINS and n >= 2 and grains < 2:
            tasks.append(f"Cook a big batch of **{ing}** (used in {n} meals), cool it quickly, and refrigerate."); minutes += 20; grains += 1
        elif ing in _LEGUMES and n >= 2 and legumes < 2:
            tasks.append(f"Cook **{ing}** in bulk (used in {n} meals)."); minutes += 25; legumes += 1
        elif ing == "egg" and n >= 3:
            tasks.append(f"Boil a batch of **eggs** (used in {n} meals)."); minutes += 10
    veg = [i for i, n in sorted(counts.items(), key=lambda x: -x[1])
           if INGR[i][0] == "produce" and i not in _FRUIT and n >= 3 and i not in ("spring onion", "mint", "cilantro")][:6]
    if veg:
        tasks.append("Wash and chop: **" + ", ".join(veg) + "** (each is used in 3 or more meals)."); minutes += 15
    batch = []
    for d in dishes:
        if "batch" in d["tags"] and d["name"] not in batch and d["type"] in ("lunch", "dinner"):
            batch.append(d["name"])
    for name in batch[:2]:
        tasks.append(f"Make a double batch of **{name}** and store portions for later."); minutes += 30
    snacks = [d["name"] for d in dishes if d["type"] == "snack" and ("batch" in d["tags"] or "quick" in d["tags"])]
    if snacks:
        tasks.append("Portion snacks into containers: " + ", ".join(sorted(set(snacks))[:3]) + "."); minutes += 10
    tips = ["Refrigerate cooked food within 2 hours and eat it within 3 to 4 days.",
            "Freeze extra portions of soups, curries, and stews, and reheat until steaming hot.",
            "Label containers with the date."]
    return {"tasks": tasks, "minutes": minutes, "tips": tips}


def prep_markdown(plan):
    pp = prep_plan(plan)
    hours = max(1, round(pp["minutes"] / 30) / 2)
    lines = [f"\U0001F9D1\u200D\U0001F373 **Meal prep checklist** (about {hours:g} hours, once a week)"] + [f"- {t}" for t in pp["tasks"]]
    lines += [""] + [f"_{t}_" for t in pp["tips"]]
    return "\n".join(lines)


def plan_markdown(plan, today=None):
    today = today or date.today()
    lines = []
    for i, day in enumerate(plan["days"]):
        names = [day[t]["name"] if day.get(t) else "-" for t in MEAL_TYPES]
        lines.append(f"- **{DAY_NAMES[i]}{' (today)' if i == today.weekday() else ''}:** " + "; ".join(names))
    return "\n".join(lines)


def week_table_markdown(plan, today=None):
    """Compact table: one row per day with breakfast, lunch, dinner, snack."""
    today = today or date.today()
    rows = ["| Day | Breakfast | Lunch | Dinner |", "|---|---|---|---|"]
    for i, day in enumerate(plan["days"]):
        cells = [day[t]["name"] if day.get(t) else "-" for t in ("breakfast", "lunch", "dinner")]
        rows.append(f"| {'**' + DAY_NAMES[i] + '**' if i == today.weekday() else DAY_NAMES[i]} | " + " | ".join(cells) + " |")
    return "\n".join(rows)
