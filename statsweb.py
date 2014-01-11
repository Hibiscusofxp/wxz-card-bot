import flask

app = flask.Flask(__name__)

leaderboard = {}

@app.route("/api/leaderboard")
def getLeaderBoard():
	return flask.jsonify(status= "success", data= leaderboard)

def launchServer():
	app.run()