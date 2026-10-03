from app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=app.config["API_HOST"],
        port=app.config["API_PORT"],
        debug=app.config["DEBUG"],
    )
