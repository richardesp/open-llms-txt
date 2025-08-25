from flask import Flask
from open_llms_txt.middleware.flask import html2md

app = Flask(__name__)

@app.get("/")
def home():
    return """
    <h1>Welcome</h1>
    <a href="/pricing">Pricing</a>
    """

@app.get("/pricing")
@html2md(app, template_name="html_to_md.jinja")
def pricing():
    return """
    <h1>Pricing Plans</h1>
    <table>
      <tr><th>Plan</th><th>Price</th><th>Features</th></tr>
      <tr><td>Free</td><td>$0</td><td>3 projects</td></tr>
      <tr><td>Pro</td><td>$29</td><td>Unlimited projects, SSO</td></tr>
    </table>
    <h2>Sign up</h2>
    <form id="signup_form" action="/signup" method="POST">
      <input type="email" name="email" required>
      <select name="plan">
        <option value="free">Free</option>
        <option value="pro">Pro</option>
      </select>
      <button type="submit">Sign up</button>
    </form>
    """

@app.post("/signup")
def signup():
    return "Thanks!"

if __name__ == "__main__":
    app.run(port=8000, debug=True)
