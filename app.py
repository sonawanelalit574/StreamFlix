import click
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from config import Config
from models import Category, MyList, User, Video, WatchHistory, db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ---------------------------------------------------------------
    # Landing / Auth
    # ---------------------------------------------------------------
    @app.route("/")
    def landing():
        if current_user.is_authenticated:
            return redirect(url_for("browse"))
        return render_template("landing.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("browse"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            error = None
            if not email or not username or not password:
                error = "All fields are required."
            elif len(password) < 6:
                error = "Password must be at least 6 characters."
            elif User.query.filter_by(email=email).first():
                error = "An account with that email already exists."
            elif User.query.filter_by(username=username).first():
                error = "That username is taken."

            if error:
                return render_template("register.html", error=error, email=email, username=username)

            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("browse"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("browse"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()

            if user and user.check_password(password):
                login_user(user, remember=True)
                next_page = request.args.get("next")
                return redirect(next_page or url_for("browse"))

            return render_template("login.html", error="Incorrect email or password.", email=email)

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("landing"))

    # ---------------------------------------------------------------
    # Browse / Home (logged in)
    # ---------------------------------------------------------------
    @app.route("/browse")
    @login_required
    def browse():
        featured = Video.query.filter_by(is_featured=True).first()
        categories = Category.query.order_by(Category.order).all()

        history = (
            WatchHistory.query.filter_by(user_id=current_user.id)
            .order_by(WatchHistory.last_watched.desc())
            .limit(12)
            .all()
        )
        continue_watching = [h for h in history if 0 < h.percent() < 95]

        return render_template(
            "browse.html",
            featured=featured,
            categories=categories,
            continue_watching=continue_watching,
        )

    # ---------------------------------------------------------------
    # Video detail + player
    # ---------------------------------------------------------------
    @app.route("/title/<int:video_id>")
    @login_required
    def title_detail(video_id):
        video = Video.query.get_or_404(video_id)
        similar = (
            Video.query.filter(Video.category_id == video.category_id, Video.id != video.id)
            .limit(8)
            .all()
        )
        in_list = MyList.query.filter_by(user_id=current_user.id, video_id=video.id).first() is not None
        history = WatchHistory.query.filter_by(user_id=current_user.id, video_id=video.id).first()
        return render_template(
            "detail.html", video=video, similar=similar, in_list=in_list, history=history
        )

    @app.route("/watch/<int:video_id>")
    @login_required
    def watch(video_id):
        video = Video.query.get_or_404(video_id)
        history = WatchHistory.query.filter_by(user_id=current_user.id, video_id=video.id).first()
        start_at = history.progress_seconds if history else 0
        return render_template("watch.html", video=video, start_at=start_at)

    # ---------------------------------------------------------------
    # Search
    # ---------------------------------------------------------------
    @app.route("/search")
    @login_required
    def search():
        q = request.args.get("q", "").strip()
        results = []
        if q:
            results = Video.query.filter(Video.title.ilike(f"%{q}%")).all()
        return render_template("search.html", query=q, results=results)

    # ---------------------------------------------------------------
    # My List
    # ---------------------------------------------------------------
    @app.route("/my-list")
    @login_required
    def my_list_page():
        items = MyList.query.filter_by(user_id=current_user.id).order_by(MyList.added_at.desc()).all()
        return render_template("my_list.html", items=items)

    @app.route("/api/mylist/<int:video_id>", methods=["POST"])
    @login_required
    def toggle_my_list(video_id):
        existing = MyList.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({"in_list": False})
        else:
            db.session.add(MyList(user_id=current_user.id, video_id=video_id))
            db.session.commit()
            return jsonify({"in_list": True})

    # ---------------------------------------------------------------
    # Watch progress (AJAX, called periodically by the player)
    # ---------------------------------------------------------------
    @app.route("/api/progress/<int:video_id>", methods=["POST"])
    @login_required
    def save_progress(video_id):
        data = request.get_json(force=True, silent=True) or {}
        progress = int(data.get("progress", 0))
        duration = int(data.get("duration", 0))

        record = WatchHistory.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        if not record:
            record = WatchHistory(user_id=current_user.id, video_id=video_id)
            db.session.add(record)

        record.progress_seconds = progress
        record.duration_seconds = duration or record.duration_seconds
        from datetime import datetime

        record.last_watched = datetime.utcnow()
        db.session.commit()
        return jsonify({"ok": True})

    # ---------------------------------------------------------------
    # CLI: seed sample data
    # ---------------------------------------------------------------
    @app.cli.command("seed")
    def seed():
        """Seed the database with sample categories and videos."""
        db.drop_all()
        db.create_all()

        categories_data = {
            "Trending Now": [
                dict(
                    title="Big Buck Bunny",
                    description=(
                        "A giant rabbit deals with three bullying rodents, in this "
                        "vibrant, open-source animated short from the Blender Foundation."
                    ),
                    thumbnail_url="https://peach.blender.org/wp-content/uploads/title_anouncement.jpg",
                    banner_url="https://peach.blender.org/wp-content/uploads/bbb-splash.png",
                    video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                    release_year=2008,
                    duration_minutes=10,
                    rating="U",
                    is_featured=True,
                    genre_tags="Animation, Comedy, Family",
                ),
                dict(
                    title="Sintel",
                    description=(
                        "A lonely young woman, Sintel, helps and befriends a dragon, "
                        "whom she names Scanty. This is the story of her search for him."
                    ),
                    thumbnail_url="https://durian.blender.org/wp-content/uploads/2010/06/05.8_comp_lighting1.1.jpg",
                    video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
                    release_year=2010,
                    duration_minutes=15,
                    rating="U/A 13+",
                    genre_tags="Fantasy, Adventure, Animation",
                ),
                dict(
                    title="Tears of Steel",
                    description=(
                        "In a near future, a group of soldiers and scientists takes "
                        "refuge in Amsterdam to build a machine that can turn back time."
                    ),
                    thumbnail_url="https://mango.blender.org/wp-content/uploads/2013/05/01_thom_celia_bridge.jpg",
                    video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
                    release_year=2012,
                    duration_minutes=12,
                    rating="U/A 16+",
                    genre_tags="Sci-Fi, Action",
                ),
            ],
            "Action & Adventure": [
                dict(
                    title="Elephants Dream",
                    description=(
                        "Two strange characters explore a capricious and seemingly "
                        "infinite machine, in the first ever open movie."
                    ),
                    thumbnail_url="https://upload.wikimedia.org/wikipedia/commons/e/e0/Elephants_Dream_s5_both.jpg",
                    video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
                    release_year=2006,
                    duration_minutes=11,
                    rating="U/A 13+",
                    genre_tags="Sci-Fi, Fantasy",
                ),
                dict(
                    title="For Bigger Blazes",
                    description="A short cinematic demo reel showcasing dynamic action and fire effects.",
                    thumbnail_url="https://i.ytimg.com/vi/Cv3ZFUyLzds/hqdefault.jpg",
                    video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                    release_year=2015,
                    duration_minutes=1,
                    rating="U/A 13+",
                    genre_tags="Action",
                ),
                dict(
                    title="For Bigger Escapes",
                    description="A high-energy montage of daring escapes and stunts.",
                    thumbnail_url="https://i.ytimg.com/vi/9OM6FIfvpBU/hqdefault.jpg",
                    video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
                    release_year=2015,
                    duration_minutes=1,
                    rating="U/A 16+",
                    genre_tags="Action, Thriller",
                ),
            ],
            "Documentaries": [
                dict(
                    title="Caminandes: Llama Drama",
                    description="Koro the llama tries to cross the road in this charming open-source short.",
                    thumbnail_url="https://i.ytimg.com/vi/skwFbxRy_Rk/hqdefault.jpg",
                    video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4",
                    release_year=2013,
                    duration_minutes=3,
                    rating="U",
                    genre_tags="Documentary, Animation",
                ),
                dict(
                    title="Subaru Outback On Street And Dirt",
                    description="A behind-the-scenes look at all-terrain vehicle testing.",
                    thumbnail_url="https://i.ytimg.com/vi/PJjXBbUlgLA/hqdefault.jpg",
                    video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4",
                    release_year=2014,
                    duration_minutes=1,
                    rating="U",
                    genre_tags="Documentary",
                ),
            ],
        }

        for order, (cat_name, videos) in enumerate(categories_data.items()):
            category = Category(name=cat_name, order=order)
            db.session.add(category)
            db.session.flush()
            for v in videos:
                db.session.add(Video(category_id=category.id, **v))

        db.session.commit()
        click.echo("Database seeded with sample categories and videos.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
