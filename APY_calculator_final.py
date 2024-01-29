"""
    author: @kpassiasGit 2024 
    free to use/read/execute 
"""
from forex_python.converter import CurrencyRates
import yfinance as yf



def get_currecyRate(from_currency, to_currency ):
    ticker_symbol = from_currency+to_currency+"=X"
    data = yf.Ticker(ticker_symbol)
    exchange_rate = data.history(period='1d')['Close'].iloc[-1]
    return exchange_rate


def exchange(capital, from_currency, to_currency):
    ticker_symbol = from_currency+to_currency+"=X"
    data = yf.Ticker(ticker_symbol)
    exchange_rate = data.history(period='1d')['Close'].iloc[-1]
    return capital * exchange_rate

def calculate_APY(capital, apy_percentage):
    apy = apy_percentage / 100
    for i in range(365):
        capital += money(capital,apy)
    return capital

def money(capital, apy):
    capital = capital*apy/365
    return capital

def customExchange(capital, prediction, from_currency, to_currency):
    ticker_symbol = from_currency+to_currency+"=X"
    data = yf.Ticker(ticker_symbol)
    exchange_rate = data.history(period='1d')['Close'].iloc[-1]
    prediction = abs(prediction-exchange_rate)
    return capital*prediction

# Read initial capital and its currency from the user
initial_capital = float(input("Enter the initial capital: "))
initial_currency = input("Enter the currency (e.g., EUR - USD - GBP): ")
print("Yahoo finance loading..")

apy_gbp = 5.12
apy_usd = 5.05
apy_eur = 3.85



# If the initial currency is GBP
if initial_currency == 'GBP':
    # Exchange to USD
    capital_usd = exchange(initial_capital, 'GBP', 'USD')
    # Calculate APY profit for USD
    capital_usd = calculate_APY(capital_usd, apy_usd)

    # Exchange to EUR
    capital_eur = exchange(initial_capital, 'GBP', 'EUR')
    # Calculate APY profit for EUR
    capital_eur = calculate_APY(capital_eur, apy_eur)

    # Re-exchange to GBP
    capital_usd = exchange(capital_usd, 'USD', 'GBP')
    capital_eur = exchange(capital_eur, 'EUR', 'GBP')
    capital_gbp = calculate_APY(initial_capital, apy_gbp)
    case = 1

elif initial_currency == 'USD':
    # Exchange to EUR
    capital_eur = exchange(initial_capital, 'USD', 'EUR')
    # Calculate APY profit for EUR
    capital_eur = calculate_APY(capital_eur, apy_eur)
    # Exchange to EUR
    capital_gbp = exchange(initial_capital, 'USD', 'GBP')
    # Calculate APY profit for EUR
    capital_gbp = calculate_APY(capital_gbp, apy_gbp)

    # Re-exchange to USD
    capital_gbp = exchange(capital_gbp, 'GBP', 'USD')
    capital_eur = exchange(capital_eur, 'EUR', 'USD')
    capital_usd = calculate_APY(initial_capital, apy_usd)
    case = 2

else:
    # Exchange to GBP
    capital_gbp = exchange(initial_capital, 'EUR', 'GBP')
    # Calculate APY profit for GBP
    capital_gbp = calculate_APY(capital_gbp, apy_gbp)
    # Exchange to USD
    capital_usd = exchange(initial_capital, 'EUR', 'USD')
    # Calculate APY profit for USD
    capital_usd = calculate_APY(capital_usd, apy_usd)

    # Re-exchange to EUR
    capital_gbp = exchange(capital_gbp, 'GBP', 'EUR')
    capital_usd = exchange(capital_usd, 'USD', 'EUR')
    capital_eur = calculate_APY(initial_capital, apy_eur)
    case = 3


rev = 16.99 * 12 - 38.88
print("Bank annual plan =", rev, "€")
print("Final profit with GBP:", round(capital_gbp - initial_capital, 3), " - Bank supply",
      round(capital_gbp - initial_capital - rev, 3), f" - {initial_currency} to GBP: ", get_currecyRate(initial_currency, 'GBP'))
print("Final profit with USD:", round(capital_usd - initial_capital, 3), " - Bank supply",
      round(capital_usd - initial_capital - rev, 3), f" - {initial_currency} to USD: ", get_currecyRate(initial_currency, 'USD'))
print("Final profit with EUR:", round(capital_eur - initial_capital, 3), " - Bank supply",
      round(capital_eur - initial_capital - rev, 3), f" - {initial_currency} to EUR: ", get_currecyRate(initial_currency, 'EUR'))


#prediction profit
while True:

    question = input(f"\n\nDo you want to predict {initial_currency} value in one year and see ur profits? (Y/N): ")
    if(question == 'Y'):
        choice = input(f"\nSelect 1 or 2 or 3 for case : \n1:{initial_currency} to GBP \n2:{initial_currency} to USD \n3:{initial_currency} to EUR\n")
        choice = int(choice)
        if choice == 1:
            gbp_val = get_currecyRate(initial_currency, 'GBP')
            print(f"Current ratio is : {gbp_val}")
            case = 1
            fcurrency = 'GBP'
            capital = capital_gbp
        elif choice == 2:
            usd_val = get_currecyRate(initial_currency, 'USD')
            print(f"Current ratio is : {usd_val}")
            case = 2
            fcurrency = 'USD'
            capital = capital_usd
        elif choice == 3:
            eur_val = get_currecyRate(initial_currency, 'EUR')
            print(f"Current ratio is : {eur_val}")
            case = 3
            fcurrency = 'EUR'
            capital = capital_eur
        else:
            continue

        prediction = float(input(f"Predict {initial_currency}: "))
        if case == 1:
            percentage = 1 + (prediction-gbp_val)
        elif case == 2:
            percentage = 1 + (prediction-usd_val)
        elif case == 3:
            percentage = 1 + (prediction-eur_val)
        
        print("Bank annual plan =", rev, "€")
        total = round((capital - initial_capital)/percentage, 3)
        print(f"Final profit with {fcurrency}:", total, " - Bank supply",round(total - rev, 3), f" - {initial_currency} to {fcurrency}: ", prediction , f"Percentage : {round(1/percentage, 3)}%")

        
    elif(question == 'N'):
        print("Exiting..")
        break
    

