import pdfplumber
import pikepdf
import io
from flask import Flask, render_template, request, flash, redirect

class NotTNGError(Exception):
    pass
class IncorrectPasswordError(Exception):
    pass

app = Flask(__name__)
# Flash messages
app.secret_key = "secret_key_for_session"

def check_pdf_password(pdf_path, password):
    #uses pikepdf to decrypt the pdf_path, if unable to decrypt, either password or pdf path is wrong
    #checks if its a tng statement or not, if no tng, pdf statement is wrong
    try:
        #open and extract
        with pikepdf.open(pdf_path, password = password) as decrypt_pdf:
            buffer = io.BytesIO()
            decrypt_pdf.save(buffer)
            buffer.seek(0)
            tng_keywords = ["tng", "wallet"]

            with pdfplumber.open(buffer) as pdf:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                #check if text exits before calling .lower()
                if text and any(kw in text.lower() for kw in tng_keywords):
                    buffer.seek(0) # Reset buffer so extract_table can read from start
                    return buffer # Return the buffer so no need decrypt later
                
                raise NotTNGError("This is not a valid TNG statement")
    
    except pikepdf.PasswordError:
        #Re-raising error for Flask route to catch it
        raise IncorrectPasswordError("The password provided is incorrect")
    
    except Exception as e:
        #Loading e for debugging
        raise e

def extract_table(buffer):
    all_rows = []
    #open the buffer using with for safety
    with pdfplumber.open(buffer) as pdf:
        #loop through every page of the pdf
        for page in pdf.pages:
            #gets the largest table on the page
            #returns a lists of lists
            table = page.extract_table() 
            if table: 
                #add the rows to the master listd
                all_rows.extend(table)  
            page.flush_cache()
    return all_rows

def parse_table(all_rows):
    # 1. Clean the table ( remove headers, 'RM' and ',' empty rows and reverse it)
    ordered_rows = all_rows[1:][::-1]
    # cleaning function
    def amount_cleaner(amount_with_rm):
        if not amount_with_rm: return 0.0
        return float(amount_with_rm.replace("RM","").replace(",","").strip())
    money_in = 0
    money_out = 0
    # TNG statement row is ['Date', 'Status', 'Transaction Type', 'Reference', 'Description', 'Details', 'Amount (RM)', 'Wallet Balance']
    # Amount in/out is index 6 or each row, final balance is index 7
    # 2. Get the value for final balance, initial balance, money in and money out
    fin_bal = amount_cleaner(ordered_rows[-1][7])
    # 3. Loop through rows to get initial balance, total money in and money out
    for i, row in enumerate(ordered_rows):
        # Break if non-cashflow row is detected
        if not row or row[0] == "Date" or row[0] is None:
            continue
        # If reached out of index, break out of loop
        if i+1 > (len(ordered_rows)-1):
            break
        cur_row_bal = amount_cleaner(row[7])
        cur_row_amn = amount_cleaner(row[6])
        nx_row_bal = amount_cleaner(ordered_rows[i+1][7])
        nx_row_amn = amount_cleaner(ordered_rows[i+1][6])
        #Getting the initial balance from first row
        if i == 0:
            # Minus the current row balance with the current row amount
            ini_bal =  round(cur_row_bal-cur_row_amn,2)
            # If the difference between initial balance and current balance is negative, its money out
            if ini_bal -  cur_row_bal < 0:
                money_in += cur_row_amn
            else:
                money_out += cur_row_amn
        #All other rows
        if cur_row_bal < nx_row_bal:
            money_in += nx_row_amn
        else:
            money_out += nx_row_amn
    # 5. Return Dict: {"initial": x, "final": y, "in":z, "out":a}
    balance = False
    # Rounding to 2 decimals
    money_in = round(money_in, 2)
    money_out = round(money_out,2)
    if round(ini_bal + money_in - money_out,2) == fin_bal:
        print("Amount balances, Success!!")
        balance = True
    return {"initial": ini_bal, "final": fin_bal, "money_in": money_in, "money_out": money_out, "balance": balance}

#Flask codes
@app.route("/", methods=["GET","POST"])
def index():
    # Parse statment if POST
    if request.method == "POST":
        file = request.files.get("file")
        password = request.form.get("password")

        #Flash messages if not file or password
        if not file or not password:
            flash("Please upload a file and enter a password")
            return redirect("/")
        
        try:
            #pass the file object directly into function
            buffer = check_pdf_password(file, password)
            if buffer:
                rows = extract_table(buffer)
                result = parse_table(rows)
                buffer.close() 
                return render_template("index.html", result=result)
        except IncorrectPasswordError:
            flash("Incorrect PDF Password")
        except NotTNGError:
            flash("Please upload a TNG pdf statement")
        except Exception as e:
            flash(f"Error: {e}. Please try again")
    # Go to homepage if GET
    return render_template("index.html", result = None)

if __name__ == "__main__":app.run(debug=True)