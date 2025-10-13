from flask import Flask
from flask_restx import Api
from api.routes.tools_ticket_store import ns as ticket_ns
from api.routes.tools_subtasks import ns as subtasks_ns
from api.routes.tools_affinity import ns as affinity_ns
from api.routes.tools_planner import ns as planner_ns
from api.routes.tools_reports import ns as reports_ns

def create_app():
    app = Flask(__name__)
    api = Api(app, title="Sprint Planner Tools", version="0.1", doc="/docs")
    api.add_namespace(ticket_ns, path="/tools/tickets")
    api.add_namespace(subtasks_ns, path="/tools/subtasks")
    api.add_namespace(affinity_ns, path="/tools/affinity")
    api.add_namespace(planner_ns, path="/tools/planner")
    api.add_namespace(reports_ns, path="/tools/reports")



    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)
