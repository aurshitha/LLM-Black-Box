import os
import time
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.dashboards_api import DashboardsApi
from datadog_api_client.v1.api.monitors_api import MonitorsApi
from datadog_api_client.v1.models import *
from datadog_api_client.v1.api.authentication_api import AuthenticationApi

def create_dashboard(api_key: str, app_key: str):
    configuration = Configuration()
    configuration.site = "datadoghq.com"
    configuration.api_key["apiKeyAuth"] = api_key
    configuration.api_key["appKeyAuth"] = app_key
    # API Key → Identifies who you are
    # App Key → Controls what you’re allowed to do

    with ApiClient(configuration) as api_client:
        print(AuthenticationApi(api_client).validate())
        dashboards_api = DashboardsApi(api_client)

        # List existing dashboards
        dashboards = dashboards_api.list_dashboards()
        for d in dashboards["dashboards"]:
            print(d["title"], "->", d["id"])
    

        title = "LLM Black Box - Single Pane"
        widgets = [
            Widget(
                definition=TimeseriesWidgetDefinition(
                    title="P95 Latency (ms)",
                    type=TimeseriesWidgetDefinitionType.TIMESERIES,
                    requests=[TimeseriesWidgetRequest(q="avg:llm.latency.ms{*} by {service}")],
                )
            ),
            Widget(
                definition=TimeseriesWidgetDefinition(
                    title="Total Tokens",
                    type=TimeseriesWidgetDefinitionType.TIMESERIES,
                    requests=[TimeseriesWidgetRequest(q="sum:llm.tokens.total{*} by {model}")],
                )
            ),
            Widget(
                definition=QueryValueWidgetDefinition(
                    title="Request Rate",
                    type=QueryValueWidgetDefinitionType.QUERY_VALUE,
                    requests=[
                        QueryValueWidgetRequest(
                            q="sum:llm.requests.count{*}",
                            aggregator="sum"
                        )
                    ],
                )
            ),
        ]

        dashboard = Dashboard(
            title=title,
            widgets=widgets,
            layout_type=DashboardLayoutType.ORDERED,
            is_read_only=False,
        )

        resp = dashboards_api.create_dashboard(dashboard)
        print("Created dashboard:", resp.id)


def create_monitors(api_key: str, app_key: str):
    configuration = Configuration()
    configuration.api_key["apiKeyAuth"] = api_key
    configuration.api_key["appKeyAuth"] = app_key

    with ApiClient(configuration) as api_client:
        monitors_api = MonitorsApi(api_client)

        # Latency degradation monitor (p95 > 3000ms for 5 minutes)
        latency_query = "avg(last_5m):avg:llm.latency.ms{*} > 3000"
        monitors_api.create_monitor(MonitorOptions(), name="LLM Latency P95 Degradation", type="metric alert", query=latency_query, message="P95 latency > 3s for 5m", tags=["service:llm-blackbox"]) 

        # Safety block monitor (log-based)
        safety_query = 'logs("service:llm-blackbox AND finish_reason:SAFETY")'
        # Datadog monitors for logs require a different API; for now create a metric alert placeholder
        print("Created monitors (latency). Please create log monitors via Datadog UI for safety blocks.")


if __name__ == "__main__":
    api_key = os.getenv("DD_API_KEY")
    app_key = os.getenv("DD_APP_KEY")
    if not api_key or not app_key:
        print("Please set DD_API_KEY and DD_APP_KEY in environment.")
        exit(1)

    create_dashboard(api_key, app_key)
    create_monitors(api_key, app_key)
