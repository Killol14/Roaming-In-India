import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from bson.errors import InvalidId
from typing import Union
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env

app = Flask(__name__) 

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)

def get_places():
    # Query the database for all documents in the "places" collection
    places = places_collection.find()

    # Check if any documents were retrieved
    if places.count() > 0:
        # Pass the retrieved documents to the "places.html" template
        return render_template("places.html", places=places)
    else:
        # If no documents were retrieved, pass a message to the "places.html" template
        return render_template("places.html", message="No places found.")


def is_logged_in() -> Union[str, None]:
    """
    Returns None if the user isn't logged in otherwise returns the username
    
    """
    return session.get("user")

@app.route("/get_places/<category>")
def filter_places(category):
    """
    Used to dynamically filter through places via the category
    """
    app.logger.info(f"Filtering with category {category}")
    places = list(mongo.db.places.find({"category_name": category.title()}))
    return render_template(
        "filtered_places.html", places=places, category=category)  

@app.route("/")
@app.route("/get_places")
def get_places():
    places = mongo.db.places.find()
    return render_template("places.html", places=places)

@app.route("/search", methods=["GET", "POST"])
def search():
    """
    Searches for both the places title and the locations
    """
    query = request.form.get("query")
    places = list(mongo.db.places.find({"$text": {"$search": query}}))
    return render_template("places.html", places=places)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Sign Up Successful!")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()}
        )

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                existing_user["password"], request.form.get("password")
            ):
                session["user"] = request.form.get("username").lower()
                flash("Hi, {}".format(request.form.get("username")))
                return redirect(url_for("account", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))
        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/account", methods=["GET", "POST"])
def account():
    if is_logged_in():
        """
        (Chat GPT)
        grab the session user's username from db
        """
        user = mongo.db.users.find_one({"username": session["user"]})
        recipes = list(mongo.db.recipes.find({"created_by": user["username"]}))
        return render_template("account.html", user=user, places=places)
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    if is_logged_in():
        # remove user from session cookie
        flash("You have been logged out, see you soon!")
        session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/delete_place/<place_id>")
def delete_place(place_id):
    if is_logged_in():
        mongo.db.places.remove({"_id": ObjectId(place_id)})
        flash("Your Added place is Deleted")
    return redirect(url_for("get_places"))

if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)