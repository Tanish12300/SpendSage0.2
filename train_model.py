# SpendSage - Simple Training Script
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

print("🪄 Training SpendSage...")

# Training data - CLEAR AND SIMPLE
descriptions = [
    # SHOPPING items (headphones goes here!)
    'headphones', 'iphone', 'laptop', 'keyboard', 'mouse', 'monitor',
    'charger', 'usb cable', 'smartwatch', 'airpods', 'speaker',
    'amazon purchase', 'target shopping', 'best buy', 'walmart',
    
    # FOOD items
    'starbucks', 'mcdonalds', 'pizza', 'burger', 'coffee',
    'restaurant', 'cafe', 'lunch', 'dinner', 'food',
    
    # ENTERTAINMENT
    'netflix', 'spotify', 'movie', 'concert', 'cinema',
    
    # TRANSPORT
    'uber', 'lyft', 'taxi', 'bus', 'train', 'gas station',
    
    # BILLS
    'electric bill', 'water bill', 'internet bill', 'phone bill',
    
    # HEALTH
    'gym', 'doctor', 'pharmacy', 'medicine',
    
    # EDUCATION
    'tuition', 'textbook', 'course', 'school supplies',
    
    # GROCERIES
    'milk', 'eggs', 'vegetables', 'grocery store',
    
    # RENT
    'rent', 'apartment', 'lease', 'housing'
]

categories = [
    # SHOPPING (15 items)
    'Shopping', 'Shopping', 'Shopping', 'Shopping', 'Shopping',
    'Shopping', 'Shopping', 'Shopping', 'Shopping', 'Shopping',
    'Shopping', 'Shopping', 'Shopping', 'Shopping', 'Shopping',
    
    # FOOD (10 items)
    'Food', 'Food', 'Food', 'Food', 'Food',
    'Food', 'Food', 'Food', 'Food', 'Food',
    
    # ENTERTAINMENT (5 items)
    'Entertainment', 'Entertainment', 'Entertainment', 'Entertainment', 'Entertainment',
    
    # TRANSPORT (6 items)
    'Transport', 'Transport', 'Transport', 'Transport', 'Transport', 'Transport',
    
    # BILLS (4 items)
    'Bills', 'Bills', 'Bills', 'Bills',
    
    # HEALTH (4 items)
    'Health', 'Health', 'Health', 'Health',
    
    # EDUCATION (4 items)
    'Education', 'Education', 'Education', 'Education',
    
    # GROCERIES (4 items)
    'Groceries', 'Groceries', 'Groceries', 'Groceries',
    
    # RENT (4 items)
    'Rent', 'Rent', 'Rent', 'Rent'
]

print(f"📊 Training on {len(descriptions)} examples...")

# Create and train
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(descriptions)
model = LogisticRegression(max_iter=1000)
model.fit(X, categories)

# Save both the vectorizer and model
with open('model.pkl', 'wb') as f:
    pickle.dump((vectorizer, model), f)

print("✅ Model saved as 'model.pkl'")

# TEST THE MODEL
print("\n🔍 TESTING:")
test_words = ['headphones', 'iphone', 'starbucks', 'netflix', 'uber', 'rent']

for word in test_words:
    test_X = vectorizer.transform([word])
    result = model.predict(test_X)[0]
    print(f"   '{word}' → {result}")

print("\n🎉 Training complete!")