# SpendSage - Ultimate Expense Tracker (All Features)
# Includes: Salary, Budget, Charts, Export, Dark Mode, Edit/Delete,
# Custom Categories, Amount Filter, Recurring Expenses, Spending Prediction,
# Monthly Comparison, Undo/Redo, Tax, Multi-wallet, Goal Setting, Excel Export,
# Email Reports (Gmail, Outlook, Yahoo, Custom SMTP)

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
import numpy as np
from sklearn.linear_model import LinearRegression
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# ----------------------------- Page Config -----------------------------
st.set_page_config(page_title="SpendSage", page_icon="🪄", layout="wide")
st.title("🪄 SpendSage")
st.markdown("*Your All‑in‑One Smart Expense Tracker*")
st.divider()

# ----------------------------- Dark Mode Toggle -----------------------------
dark_mode = st.toggle("🌙 Dark Mode", value=False)
if dark_mode:
    st.markdown("""
        <style>
        .stApp { background-color: #1e1e1e; color: #ffffff; }
        .stButton button { background-color: #4CAF50; color: white; }
        .stMetric { background-color: #2d2d2d; border-radius: 10px; padding: 10px; }
        </style>
    """, unsafe_allow_html=True)

# ----------------------------- Currency Options -----------------------------
currencies = {
    "🇮🇳 Indian Rupee (INR)": {"symbol": "₹", "code": "INR"},
    "🇺🇸 US Dollar (USD)": {"symbol": "$", "code": "USD"},
    "🇪🇺 Euro (EUR)": {"symbol": "€", "code": "EUR"},
    "🇬🇧 British Pound (GBP)": {"symbol": "£", "code": "GBP"},
    "🇯🇵 Japanese Yen (JPY)": {"symbol": "¥", "code": "JPY"},
}

# ----------------------------- Session State Init -----------------------------
if 'expenses' not in st.session_state:
    st.session_state.expenses = pd.DataFrame(columns=['date', 'description', 'amount', 'currency', 'category', 'account'])
if 'salary' not in st.session_state:
    st.session_state.salary = 0.0
if 'last_added' not in st.session_state:
    st.session_state.last_added = None
if 'budget_limits' not in st.session_state:
    st.session_state.budget_limits = {}
if 'custom_categories' not in st.session_state:
    st.session_state.custom_categories = ["Food", "Shopping", "Entertainment", "Transport", "Bills", "Health", "Education", "Groceries", "Rent"]
if 'recurring' not in st.session_state:
    st.session_state.recurring = []  # list of dicts: {amount, category, description, day_of_month, account}
if 'tax_rate' not in st.session_state:
    st.session_state.tax_rate = 0.0
if 'accounts' not in st.session_state:
    st.session_state.accounts = ["Cash", "Bank", "Credit Card", "UPI"]
if 'savings_goal' not in st.session_state:
    st.session_state.savings_goal = 0.0
if 'history_undo_stack' not in st.session_state:
    st.session_state.history_undo_stack = []
if 'history_redo_stack' not in st.session_state:
    st.session_state.history_redo_stack = []

# ----------------------------- Helper Functions -----------------------------
def format_currency(amount):
    return f"{currency_symbol}{amount:,.2f}"

def get_total_spent(df):
    return df['amount'].sum() if not df.empty else 0

def get_remaining_salary():
    if st.session_state.salary > 0:
        return st.session_state.salary - get_total_spent(st.session_state.expenses)
    return None

def add_expense(date, description, amount, category, account):
    new_row = pd.DataFrame({
        'date': [date],
        'description': [description],
        'amount': [amount],
        'currency': [currency_code],
        'category': [category],
        'account': [account]
    })
    st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)

def push_undo_state():
    st.session_state.history_undo_stack.append(st.session_state.expenses.copy())
    st.session_state.history_redo_stack.clear()

def undo():
    if st.session_state.history_undo_stack:
        st.session_state.history_redo_stack.append(st.session_state.expenses.copy())
        st.session_state.expenses = st.session_state.history_undo_stack.pop()
        st.rerun()

def redo():
    if st.session_state.history_redo_stack:
        st.session_state.history_undo_stack.append(st.session_state.expenses.copy())
        st.session_state.expenses = st.session_state.history_redo_stack.pop()
        st.rerun()

def process_recurring():
    today = datetime.now()
    for rec in st.session_state.recurring:
        if today.day == rec['day_of_month']:
            already_added = not st.session_state.expenses[
                (st.session_state.expenses['description'] == rec['description']) & 
                (pd.to_datetime(st.session_state.expenses['date']).dt.date == today.date())
            ].empty
            if not already_added:
                add_expense(today.date(), rec['description'], rec['amount'], rec['category'], rec['account'])
                st.session_state.last_added = f"Recurring: {rec['description']} - {format_currency(rec['amount'])}"

def predict_spending():
    if len(st.session_state.expenses) < 3:
        return None
    df = st.session_state.expenses.copy()
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
    monthly = df.groupby('month')['amount'].sum().reset_index()
    monthly['month_num'] = range(1, len(monthly)+1)
    if len(monthly) < 2:
        return None
    X = monthly['month_num'].values.reshape(-1,1)
    y = monthly['amount'].values
    model = LinearRegression()
    model.fit(X, y)
    next_month_num = len(monthly) + 1
    prediction = model.predict([[next_month_num]])[0]
    return max(0, prediction)

def compare_months():
    if st.session_state.expenses.empty:
        return None
    df = st.session_state.expenses.copy()
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
    current = df[df['month'] == df['month'].max()]['amount'].sum()
    prev = df[df['month'] == df['month'].max() - 1]['amount'].sum() if len(df['month'].unique()) > 1 else 0
    return current, prev

# ----------------------------- Sidebar -----------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    selected_currency = st.selectbox("Select Currency", list(currencies.keys()))
    currency_symbol = currencies[selected_currency]["symbol"]
    currency_code = currencies[selected_currency]["code"]
    
    st.divider()
    st.header("💰 Salary")
    salary_input = st.number_input(f"Monthly Salary ({currency_symbol})", min_value=0.0, step=1000.0,
                                   value=float(st.session_state.salary))
    if st.button("Set Salary", use_container_width=True):
        st.session_state.salary = salary_input
        st.success(f"Salary set to {currency_symbol}{salary_input:,.2f}")
        st.rerun()
    
    if st.session_state.salary > 0:
        st.info(f"Salary: {currency_symbol}{st.session_state.salary:,.2f}")
    
    st.divider()
    st.header("🎯 Custom Categories")
    new_cat = st.text_input("Add new category")
    if st.button("Add Category"):
        if new_cat and new_cat not in st.session_state.custom_categories:
            st.session_state.custom_categories.append(new_cat)
            st.rerun()
    for cat in st.session_state.custom_categories:
        col1, col2 = st.columns([3,1])
        with col1:
            st.write(cat)
        with col2:
            if st.button("❌", key=f"del_cat_{cat}"):
                st.session_state.custom_categories.remove(cat)
                st.rerun()
    
    st.divider()
    st.header("🎯 Budget Limits")
    for cat in st.session_state.custom_categories:
        if cat not in st.session_state.budget_limits:
            st.session_state.budget_limits[cat] = 5000
        st.session_state.budget_limits[cat] = st.number_input(f"{cat} Budget", min_value=0,
                                                              value=st.session_state.budget_limits[cat],
                                                              key=f"budget_{cat}")
    
    st.divider()
    st.header("💰 Accounts")
    new_acc = st.text_input("New account name")
    if st.button("Add Account"):
        if new_acc and new_acc not in st.session_state.accounts:
            st.session_state.accounts.append(new_acc)
            st.rerun()
    for acc in st.session_state.accounts:
        col1, col2 = st.columns([3,1])
        with col1:
            st.write(acc)
        with col2:
            if st.button("❌", key=f"del_acc_{acc}"):
                st.session_state.accounts.remove(acc)
                st.rerun()
    
    st.divider()
    st.header("🧾 Tax Rate (%)")
    st.session_state.tax_rate = st.number_input("Global Tax Rate (%)", min_value=0.0, max_value=100.0, value=st.session_state.tax_rate, step=0.5)
    
    st.divider()
    st.header("🎯 Savings Goal")
    st.session_state.savings_goal = st.number_input(f"Monthly Savings Goal ({currency_symbol})", min_value=0.0, value=st.session_state.savings_goal, step=500.0)
    
    st.divider()
    page = st.radio("📱 Navigate", ["➕ Add Expense", "📜 History", "📈 Dashboard", "💰 Salary View", "🔄 Recurring", "📧 Email Reports", "📥 Backup & Export"])

# Process recurring expenses on each load
process_recurring()

# ============================= PAGE 1: ADD EXPENSE =============================
if page == "➕ Add Expense":
    st.subheader("➕ Add New Expense")
    
    if st.session_state.last_added:
        st.success(f"✅ Added: {st.session_state.last_added}")
    
    # JavaScript: Enter moves to next field, never submits
    st.markdown("""
        <script>
            (function() {
                function setupEnterNavigation() {
                    const form = document.querySelector('form');
                    if (!form) return;
                    const focusable = Array.from(form.querySelectorAll(
                        'input:not([type="hidden"]), select, [data-baseweb="datepicker"] input'
                    )).filter(el => !el.disabled);
                    focusable.forEach((el, idx) => {
                        el.removeEventListener('keydown', window._enterHandler);
                        const handler = function(e) {
                            if (e.key === 'Enter') {
                                e.preventDefault();
                                e.stopPropagation();
                                if (idx < focusable.length - 1) {
                                    focusable[idx + 1].focus();
                                }
                                return false;
                            }
                        };
                        el.addEventListener('keydown', handler);
                        window._enterHandler = handler;
                    });
                }
                setTimeout(setupEnterNavigation, 500);
                const observer = new MutationObserver(() => setTimeout(setupEnterNavigation, 200));
                observer.observe(document.body, { childList: true, subtree: true });
            })();
        </script>
    """, unsafe_allow_html=True)
    
    # Form state initialisation (no manual reset after submission)
    if 'form_description' not in st.session_state:
        st.session_state.form_description = ""
    if 'form_amount' not in st.session_state:
        st.session_state.form_amount = 0.0
    if 'form_date' not in st.session_state:
        st.session_state.form_date = datetime.now()
    if 'form_category' not in st.session_state:
        st.session_state.form_category = st.session_state.custom_categories[0] if st.session_state.custom_categories else "Food"
    if 'form_account' not in st.session_state:
        st.session_state.form_account = st.session_state.accounts[0] if st.session_state.accounts else "Cash"
    
    with st.form(key="expense_form", clear_on_submit=True):   # auto‑clear fields after submit
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("What did you buy?", placeholder="e.g., Starbucks, Netflix", key="form_description")
        with col2:
            st.number_input(f"Amount ({currency_symbol})", min_value=0.0, step=0.01, value=0.00, key="form_amount")
        
        st.date_input("Date", datetime.now(), key="form_date")
        st.selectbox("Category", st.session_state.custom_categories, key="form_category")
        st.selectbox("Account", st.session_state.accounts, key="form_account")
        
        submitted = st.form_submit_button("💾 Save Expense", use_container_width=True, type="primary")
        
        if submitted:
            if st.session_state.form_description and st.session_state.form_amount > 0:
                push_undo_state()
                add_expense(
                    st.session_state.form_date,
                    st.session_state.form_description,
                    st.session_state.form_amount,
                    st.session_state.form_category,
                    st.session_state.form_account
                )
                st.session_state.last_added = f"{st.session_state.form_description} - {currency_symbol}{st.session_state.form_amount:.2f}"
                st.success("Saved!")
                st.balloons()
                st.rerun()
            else:
                st.error("Please fill both description and amount")
    
    if not st.session_state.expenses.empty:
        st.divider()
        st.subheader("📋 Recent Expenses")
        recent = st.session_state.expenses.tail(5).copy()
        recent['amount'] = recent['amount'].apply(format_currency)
        st.dataframe(recent[['date', 'description', 'amount', 'category', 'account']], use_container_width=True)

# ============================= PAGE 2: HISTORY =============================
elif page == "📜 History":
    st.subheader("📜 Expense History")
    col_undo, col_redo = st.columns(2)
    with col_undo:
        if st.button("↩️ Undo", use_container_width=True):
            undo()
    with col_redo:
        if st.button("↪️ Redo", use_container_width=True):
            redo()
    st.divider()
    
    if st.session_state.expenses.empty:
        st.info("No expenses yet. Add some!")
    else:
        # Filtering
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_type = st.selectbox("Time Filter", ["All Time", "This Month", "Last Month", "Custom Range"])
        with col_f2:
            search = st.text_input("🔍 Search", placeholder="Type to filter description")
        
        df = st.session_state.expenses.copy()
        now = datetime.now()
        if filter_type == "This Month":
            df = df[pd.to_datetime(df['date']).dt.month == now.month]
        elif filter_type == "Last Month":
            last = now.replace(day=1) - timedelta(days=1)
            df = df[pd.to_datetime(df['date']).dt.month == last.month]
        elif filter_type == "Custom Range":
            col_a, col_b = st.columns(2)
            with col_a:
                start = st.date_input("From", datetime.now().replace(day=1))
            with col_b:
                end = st.date_input("To", datetime.now())
            df = df[(pd.to_datetime(df['date']) >= pd.to_datetime(start)) & (pd.to_datetime(df['date']) <= pd.to_datetime(end))]
        
        if search:
            df = df[df['description'].str.contains(search, case=False)]
        
        # Amount range filter
        if not df.empty:
            min_amount = st.slider("Min Amount", 0.0, float(df['amount'].max()), 0.0, step=50.0)
            max_amount = st.slider("Max Amount", 0.0, float(df['amount'].max()), float(df['amount'].max()), step=50.0)
            df = df[(df['amount'] >= min_amount) & (df['amount'] <= max_amount)]
        
        # Account filter
        accounts = ["All"] + st.session_state.accounts
        selected_account = st.selectbox("Filter by Account", accounts)
        if selected_account != "All":
            df = df[df['account'] == selected_account]
        
        # Total and tax
        total = df['amount'].sum()
        tax = total * (st.session_state.tax_rate / 100)
        st.metric("💰 Total for selected period", format_currency(total))
        if st.session_state.tax_rate > 0:
            st.metric("🧾 Estimated Tax", format_currency(tax))
        
        # Remaining if salary set
        if st.session_state.salary > 0:
            remaining = st.session_state.salary - get_total_spent(st.session_state.expenses)
            st.metric("💰 Remaining (overall)", format_currency(remaining))
        
        st.divider()
        
        # Display each row with edit/delete
        for idx, row in df.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 2, 2, 2, 1.5, 1, 1])
            with col1:
                st.write(row['description'])
            with col2:
                st.write(format_currency(row['amount']))
            with col3:
                st.write(str(row['date']))
            with col4:
                st.write(row['category'])
            with col5:
                st.write(row['account'])
            with col6:
                if st.button(f"✏️", key=f"edit_{idx}"):
                    new_amount = st.number_input("New amount", value=row['amount'], key=f"newamt_{idx}")
                    if st.button("Update", key=f"upd_{idx}"):
                        push_undo_state()
                        st.session_state.expenses.at[idx, 'amount'] = new_amount
                        st.rerun()
            with col7:
                if st.button(f"🗑️", key=f"del_{idx}"):
                    push_undo_state()
                    st.session_state.expenses.drop(idx, inplace=True)
                    st.rerun()
        
        # Clear all
        if st.button("🗑️ Clear All History", type="secondary"):
            push_undo_state()
            st.session_state.expenses = pd.DataFrame(columns=['date', 'description', 'amount', 'currency', 'category', 'account'])
            st.rerun()

# ============================= PAGE 3: DASHBOARD =============================
elif page == "📈 Dashboard":
    st.subheader("📊 Spending Dashboard")
    
    if st.session_state.expenses.empty:
        st.info("No data to display. Add expenses first.")
    else:
        df = st.session_state.expenses.copy()
        total = get_total_spent(df)
        
        # Salary overview card
        if st.session_state.salary > 0:
            remaining = st.session_state.salary - total
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Monthly Salary", format_currency(st.session_state.salary))
            with col2:
                st.metric("💸 Total Spent", format_currency(total))
            with col3:
                st.metric("✅ Money Left", format_currency(remaining))
            spent_percent = (total / st.session_state.salary) * 100
            st.progress(min(spent_percent/100, 1.0))
            st.caption(f"Used {spent_percent:.1f}% of salary")
            st.divider()
        
        # Spending prediction
        pred = predict_spending()
        if pred:
            st.info(f"🔮 Predicted spending this month: {format_currency(pred)}")
        
        # Monthly comparison
        comp = compare_months()
        if comp:
            current_month, prev_month = comp
            if prev_month > 0:
                change = ((current_month - prev_month) / prev_month) * 100
                if change > 0:
                    st.warning(f"📈 Spending increased by {change:.1f}% compared to previous month")
                elif change < 0:
                    st.success(f"📉 Spending decreased by {abs(change):.1f}% compared to previous month")
                else:
                    st.info("Spending same as previous month")
        
        # Goal progress
        if st.session_state.savings_goal > 0 and st.session_state.salary > 0:
            savings = st.session_state.salary - total
            percent = min(100, (savings / st.session_state.savings_goal) * 100) if st.session_state.savings_goal > 0 else 0
            st.subheader("🏆 Savings Goal Progress")
            st.progress(percent/100)
            st.caption(f"Saved: {format_currency(savings)} / Goal: {format_currency(st.session_state.savings_goal)} ({percent:.0f}%)")
            if savings >= st.session_state.savings_goal:
                st.balloons()
                st.success("🎉 Congratulations! You reached your savings goal!")
        
        st.divider()
        
        # Charts
        col_ch1, col_ch2 = st.columns(2)
        with col_ch1:
            st.subheader("📈 Spending Trend")
            if len(df) > 1:
                trend = df.groupby('date')['amount'].sum().reset_index()
                fig = px.line(trend, x='date', y='amount', markers=True, title="Daily Spending")
                fig.update_traces(line=dict(color='#4CAF50', width=3))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Add at least 2 transactions to see trend")
        
        with col_ch2:
            st.subheader("🥧 Category Breakdown")
            cat_sum = df.groupby('category')['amount'].sum().reset_index()
            fig = px.pie(cat_sum, values='amount', names='category', hole=0.3, title="Spending by Category")
            st.plotly_chart(fig, use_container_width=True)
        
        # Budget Alerts
        st.subheader("⚠️ Budget Alerts")
        for cat, limit in st.session_state.budget_limits.items():
            spent = df[df['category'] == cat]['amount'].sum() if cat in df['category'].values else 0
            percent = (spent / limit) * 100 if limit > 0 else 0
            if percent > 100:
                st.error(f"🚨 {cat}: {format_currency(spent)} / {format_currency(limit)} ({percent:.0f}% OVER BUDGET!)")
            elif percent > 80:
                st.warning(f"⚠️ {cat}: {format_currency(spent)} / {format_currency(limit)} ({percent:.0f}% near limit)")
            else:
                st.info(f"✅ {cat}: {format_currency(spent)} / {format_currency(limit)} ({percent:.0f}%)")
        
        # Account breakdown
        st.subheader("💳 Spending by Account")
        acc_sum = df.groupby('account')['amount'].sum().reset_index()
        fig_acc = px.bar(acc_sum, x='account', y='amount', title="Total by Account", color='account')
        st.plotly_chart(fig_acc, use_container_width=True)
        
        # Top expenses
        st.subheader("🔥 Top 5 Expenses")
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0) 
        top = df.nlargest(5, 'amount')[['date', 'description', 'amount', 'category', 'account']].copy()
        top['amount'] = top['amount'].apply(format_currency)
        st.dataframe(top, use_container_width=True)

# ============================= PAGE 4: SALARY VIEW =============================
elif page == "💰 Salary View":
    st.subheader("💰 Salary & Financial Overview")
    
    if st.session_state.salary == 0:
        st.warning("Please set your monthly salary in the sidebar first!")
    else:
        total_spent = get_total_spent(st.session_state.expenses)
        remaining = st.session_state.salary - total_spent
        percent_used = (total_spent / st.session_state.salary) * 100
        percent_saved = max((remaining / st.session_state.salary) * 100, 0)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Salary", format_currency(st.session_state.salary))
        with col2:
            st.metric("💸 Spent", format_currency(total_spent))
        with col3:
            st.metric("✅ Left", format_currency(remaining))
        
        st.subheader("📊 Budget Usage")
        st.progress(min(percent_used/100, 1.0))
        st.caption(f"Spent: {percent_used:.1f}% | Saved: {percent_saved:.1f}%")
        
        # Simple bar chart
        fig = px.bar(x=['Salary', 'Spent', 'Left'], y=[st.session_state.salary, total_spent, max(remaining, 0)],
                     title="Salary Breakdown", color=['Salary', 'Spent', 'Left'],
                     color_discrete_map={'Salary': '#2196F3', 'Spent': '#FF6B6B', 'Left': '#4CAF50'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Advice
        st.subheader("💡 Financial Advice")
        if remaining < 0:
            st.error(f"⚠️ You overspent by {format_currency(abs(remaining))}. Review expenses and cut unnecessary costs!")
        elif remaining < st.session_state.salary * 0.1:
            st.warning(f"📉 You're saving only {percent_saved:.1f}% of your salary. Try to reduce dining out and subscriptions.")
        elif remaining < st.session_state.salary * 0.2:
            st.info(f"📈 Good! You're saving {percent_saved:.1f}%. Aim for 20% to build wealth faster.")
        else:
            st.success(f"🎉 Excellent! You're saving {percent_saved:.1f}% of your salary. Consider investing the surplus!")

# ============================= PAGE 5: RECURRING =============================
elif page == "🔄 Recurring":
    st.subheader("🔄 Manage Recurring Expenses")
    
    st.write("Add monthly recurring expenses (e.g., Rent, Netflix). They will be added automatically on the selected day of each month.")
    
    with st.form("recurring_form"):
        col1, col2 = st.columns(2)
        with col1:
            rec_desc = st.text_input("Description", placeholder="e.g., Netflix Subscription")
        with col2:
            rec_amount = st.number_input(f"Amount ({currency_symbol})", min_value=0.0, step=50.0, value=0.0)
        rec_category = st.selectbox("Category", st.session_state.custom_categories)
        rec_account = st.selectbox("Account", st.session_state.accounts)
        rec_day = st.slider("Day of month (1-28)", min_value=1, max_value=28, value=1)
        if st.form_submit_button("Add Recurring Expense"):
            if rec_desc and rec_amount > 0:
                st.session_state.recurring.append({
                    'description': rec_desc,
                    'amount': rec_amount,
                    'category': rec_category,
                    'account': rec_account,
                    'day_of_month': rec_day
                })
                st.success("Recurring expense added!")
                st.rerun()
    
    if st.session_state.recurring:
        st.divider()
        st.subheader("📋 Current Recurring Expenses")
        for i, rec in enumerate(st.session_state.recurring):
            col1, col2, col3, col4, col5 = st.columns([3,2,2,2,1])
            with col1:
                st.write(rec['description'])
            with col2:
                st.write(format_currency(rec['amount']))
            with col3:
                st.write(rec['category'])
            with col4:
                st.write(f"Day {rec['day_of_month']}")
            with col5:
                if st.button("❌", key=f"del_rec_{i}"):
                    st.session_state.recurring.pop(i)
                    st.rerun()

# ============================= PAGE 6: EMAIL REPORTS =============================
elif page == "📧 Email Reports":
    st.subheader("📧 Send Expense Reports by Email")
    
    st.markdown("""
    ### Configure your email settings
    Enter your SMTP details. For Gmail, you need an **App Password** (not your regular password).
    [How to get a Gmail App Password](https://support.google.com/accounts/answer/185833)
    """)
    
    with st.form("email_form"):
        col1, col2 = st.columns(2)
        with col1:
            email_provider = st.selectbox("Email Provider", ["Gmail", "Outlook/Hotmail", "Yahoo", "Custom SMTP"])
            if email_provider == "Gmail":
                smtp_server = "smtp.gmail.com"
                smtp_port = 587
            elif email_provider == "Outlook/Hotmail":
                smtp_server = "smtp-mail.outlook.com"
                smtp_port = 587
            elif email_provider == "Yahoo":
                smtp_server = "smtp.mail.yahoo.com"
                smtp_port = 587
            else:
                smtp_server = st.text_input("SMTP Server", "smtp.example.com")
                smtp_port = st.number_input("SMTP Port", value=587, step=1)
        
        with col2:
            sender_email = st.text_input("Your Email Address")
            password = st.text_input("Email Password or App Password", type="password")
            recipient_email = st.text_input("Recipient Email Address", value=sender_email)
        
        st.divider()
        st.subheader("Report Options")
        report_type = st.radio("Report Type", ["This Month", "Last 7 Days", "Custom Range"])
        if report_type == "Custom Range":
            start_date = st.date_input("Start Date", datetime.now().replace(day=1))
            end_date = st.date_input("End Date", datetime.now())
        
        send_test = st.form_submit_button("✉️ Send Test Email", use_container_width=True)
        send_report = st.form_submit_button("📊 Send Full Report", use_container_width=True, type="primary")
        
        if send_test or send_report:
            if not sender_email or not password or not recipient_email:
                st.error("Please fill in email, password, and recipient address.")
            else:
                try:
                    # Determine date range
                    if report_type == "This Month":
                        start = datetime.now().replace(day=1).date()
                        end = datetime.now().date()
                    elif report_type == "Last 7 Days":
                        start = (datetime.now() - timedelta(days=7)).date()
                        end = datetime.now().date()
                    else:
                        start = start_date
                        end = end_date
                    
                    # Filter expenses
                    filtered = st.session_state.expenses[
                        (pd.to_datetime(st.session_state.expenses['date']).dt.date >= start) &
                        (pd.to_datetime(st.session_state.expenses['date']).dt.date <= end)
                    ]
                    
                    total = filtered['amount'].sum() if not filtered.empty else 0
                    
                    # Prepare email content
                    msg = MIMEMultipart()
                    msg['From'] = sender_email
                    msg['To'] = recipient_email
                    
                    if send_test:
                        msg['Subject'] = "SpendSage - Test Email"
                        body = f"""
                        <h2>✅ SpendSage Test Email</h2>
                        <p>Your email settings are working correctly!</p>
                        <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>Currency: {currency_code} ({currency_symbol})</p>
                        """
                    else:
                        msg['Subject'] = f"SpendSage Expense Report ({start} to {end})"
                        body = f"""
                        <h2>📊 SpendSage Expense Report</h2>
                        <p><strong>Period:</strong> {start} to {end}</p>
                        <p><strong>Total Expenses:</strong> {currency_symbol}{total:,.2f}</p>
                        <p><strong>Number of Transactions:</strong> {len(filtered)}</p>
                        <hr>
                        <h3>🔍 Top 5 Expenses</h3>
                        <ul>
                        """
                        if not filtered.empty:
                            top = filtered.nlargest(5, 'amount')
                            for _, row in top.iterrows():
                                body += f"<li>{row['date']} - {row['description']}: {currency_symbol}{row['amount']:.2f} ({row['category']})</li>\n"
                            body += "</ul><hr><h3>📈 Summary by Category</h3><ul>"
                            cat_sum = filtered.groupby('category')['amount'].sum().head(10)
                            for cat, amt in cat_sum.items():
                                body += f"<li>{cat}: {currency_symbol}{amt:.2f}</li>\n"
                            body += "</ul>"
                        else:
                            body += "<li>No expenses in this period.</li></ul>"
                        
                        # Add salary & savings info if salary set
                        if st.session_state.salary > 0:
                            remaining = st.session_state.salary - get_total_spent(st.session_state.expenses)
                            body += f"<hr><h3>💰 Financial Overview</h3>"
                            body += f"<p>Monthly Salary: {currency_symbol}{st.session_state.salary:,.2f}</p>"
                            body += f"<p>Total Spent: {currency_symbol}{get_total_spent(st.session_state.expenses):,.2f}</p>"
                            body += f"<p>Remaining: {currency_symbol}{remaining:,.2f}</p>"
                    
                    msg.attach(MIMEText(body, 'html'))
                    
                    # Attach CSV for full report
                    if send_report and not filtered.empty:
                        csv_buffer = io.StringIO()
                        filtered.to_csv(csv_buffer, index=False)
                        csv_data = csv_buffer.getvalue().encode('utf-8')
                        attachment = MIMEBase('application', 'octet-stream')
                        attachment.set_payload(csv_data)
                        encoders.encode_base64(attachment)
                        attachment.add_header('Content-Disposition', 'attachment', filename=f"spendsage_{start}_{end}.csv")
                        msg.attach(attachment)
                    
                    # Send email
                    with smtplib.SMTP(smtp_server, smtp_port) as server:
                        server.starttls()
                        server.login(sender_email, password)
                        server.send_message(msg)
                    
                    if send_test:
                        st.success("✅ Test email sent! Check your inbox (and spam folder).")
                    else:
                        st.success(f"📧 Expense report sent to {recipient_email}!")
                        st.balloons()
                except Exception as e:
                    st.error(f"Failed to send email: {e}")
                    st.info("Check your SMTP settings, password (App Password for Gmail), and network.")
    
    st.caption("💡 Tip: For Gmail, use an App Password. For Outlook/Yahoo, normal password may work with 2FA off (not recommended). For security, use app-specific passwords.")

# ============================= PAGE 7: BACKUP & EXPORT =============================
elif page == "📥 Backup & Export":
    st.subheader("📥 Data Backup & Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Export as CSV")
        if not st.session_state.expenses.empty:
            csv = st.session_state.expenses.to_csv(index=False)
            st.download_button("Download CSV", csv, f"spendsage_{datetime.now().strftime('%Y%m%d')}.csv")
        else:
            st.info("No data to export")
    
    with col2:
        st.subheader("📗 Export as Excel")
        if not st.session_state.expenses.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.expenses.to_excel(writer, sheet_name='Expenses', index=False)
                summary = pd.DataFrame({
                    'Metric': ['Total Spent', 'Salary', 'Remaining', 'Tax Rate', 'Savings Goal'],
                    'Value': [
                        get_total_spent(st.session_state.expenses),
                        st.session_state.salary,
                        st.session_state.salary - get_total_spent(st.session_state.expenses) if st.session_state.salary else 0,
                        f"{st.session_state.tax_rate}%",
                        st.session_state.savings_goal
                    ]
                })
                summary.to_excel(writer, sheet_name='Summary', index=False)
            excel_data = output.getvalue()
            st.download_button("Download Excel", excel_data, f"spendsage_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("No data to export")
    
    st.divider()
    st.subheader("💾 Backup (JSON)")
    if not st.session_state.expenses.empty:
        backup_data = {
            'expenses': st.session_state.expenses.to_dict('records'),
            'salary': st.session_state.salary,
            'budget_limits': st.session_state.budget_limits,
            'custom_categories': st.session_state.custom_categories,
            'recurring': st.session_state.recurring,
            'tax_rate': st.session_state.tax_rate,
            'accounts': st.session_state.accounts,
            'savings_goal': st.session_state.savings_goal
        }
        backup_json = json.dumps(backup_data, indent=2, default=str)
        st.download_button("Download Backup", backup_json, "spendsage_backup.json")
    else:
        st.info("No data to backup")
    
    st.divider()
    st.subheader("🔄 Restore from Backup")
    uploaded = st.file_uploader("Choose backup file", type=['json'])
    if uploaded:
        try:
            data = json.load(uploaded)
            st.session_state.expenses = pd.DataFrame(data['expenses'])
            st.session_state.salary = data.get('salary', 0)
            if 'budget_limits' in data:
                st.session_state.budget_limits = data['budget_limits']
            if 'custom_categories' in data:
                st.session_state.custom_categories = data['custom_categories']
            if 'recurring' in data:
                st.session_state.recurring = data['recurring']
            if 'tax_rate' in data:
                st.session_state.tax_rate = data['tax_rate']
            if 'accounts' in data:
                st.session_state.accounts = data['accounts']
            if 'savings_goal' in data:
                st.session_state.savings_goal = data['savings_goal']
            st.success("✅ Restore successful! Refreshing...")
            st.rerun()
        except Exception as e:
            st.error(f"Invalid backup file: {e}")

# ----------------------------- Footer -----------------------------
st.divider()
st.caption(f"🪄 SpendSage - {currency_code} | All-in-One Expense Tracker | Made with ❤️")