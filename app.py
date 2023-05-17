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

def is_logged_in() -> Union[str, None]:
    return session.get("user")

@app.route("/")
@app.route("/home")
def home():
    return render_template("index.html")


@app.route("/get_places/<category>")
def filter_places(category):
    app.logger.info(f"Filtering with category {category}")
    places = list(mongo.db.places.find({"category_name": category.title()}))
    return render_template(
        "filtered_places.html", places=places, category=category)  

@app.route("/get_places")
def get_places():
    places = list(mongo.db.places.find()) 
    return render_template("places.html", places=places)

@app.route("/search", methods=["GET", "POST"])
def search():
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
        flash("Registration Successful!")
        return redirect(url_for("account", username=session["user"]))
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
        user = mongo.db.users.find_one({"username": session["user"]})
        places = list(mongo.db.recipes.find({"created_by": user["username"]}))
        return render_template("account.html", user=user, places=places)
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    if is_logged_in():
        # remove user from session cookie
        flash("You have been logged out, see you soon!")
        session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/add_place", methods=["GET", "POST"])
def add_place():
    # adds place to database
    if is_logged_in() and request.method == "POST":
        place = {
            "category_name": request.form.get("category_name"),
            "place_name": request.form.get("place_name"),
            "location": request.form.get("location"),
            "description": request.form.get("description"),
            "image_url": request.form.get("image_url"),
            "created_by": session["user"],
        }
        mongo.db.places.insert_one(place)
        flash("place Successfully Added")
        return redirect(url_for("get_places"))

    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("add_place.html", categories=categories)

@app.route("/edit_place/<place_id>", methods=["GET", "POST"])
def edit_place(place_id):
    # updates places in database
    if is_logged_in() and request.method == "POST":
        submit = {
            "category_name": request.form.get("category_name"),
            "place_name": request.form.get("place_name"),
            "location": request.form.get("location"),
            "description": request.form.get("description"),
            "image_url": request.form.get("image_url"),
            "created_by": session["user"],
        }
        mongo.db.places.update_one({"_id": ObjectId(place_id)}, {'$set': submit})
        flash("Your added Place Is Updated!")
       

    place = mongo.db.places.find_one({"_id": ObjectId(place_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("edit_place.html", place=place, categories=categories)

@app.route("/delete_place/<place_id>")
def delete_place(place_id):
    if is_logged_in():
        mongo.db.places.delete_one({"_id": ObjectId(place_id)})
        flash("Your Added place is Deleted")
    return redirect(url_for("get_places"))

@app.route("/get_categories")
def get_categories():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("categories.html", categories=categories)

@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    if request.method == "POST":
        category = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.insert_one(category)
        flash("New Category Added")
        return redirect(url_for("get_categories"))

    return render_template("add_category.html")


@app.route("/edit_category/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    if request.method == "POST":
        submit = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.update_one({"_id": ObjectId(category_id)},{"$set": submit})
        flash("Category Updated")
        return redirect(url_for("get_categories"))

    category = mongo.db.categories.find_one({"_id": ObjectId(category_id)})
    return render_template("edit_category.html", category=category)


@app.route("/delete_category/<category_id>")
def delete_category(category_id):
    mongo.db.categories.delete_one({"_id": ObjectId(category_id)})
    flash("Category Deleted")
    return redirect(url_for("get_categories"))   

# this error code copied from third party
@app.errorhandler(404)
def not_found_error(error):
    """
    404 error page, code referenced from:
    https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-vii-error-handling
    """
    return (
        render_template(
            "error.html",
            error_message="We can't find the page you're looking for",
            error_title="Oooops...",
        ),
        404,
    )

# this error code copied from third party

@app.errorhandler(Exception)
def server_error(error):
    """
    Catches any potential exception which is then handled according
    to the instance type
    """
    error_title = "Oooops..."
    if isinstance(error, InvalidId):
        error_message = "Couldn't find it in the database"
    else:
        error_message = "Something went wrong"
    return (
        render_template(
            "error.html", error_message=error_message, error_title=error_title
        ),
        500,
    )
if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)