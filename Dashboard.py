# =====================================================
# 1. IMPORT LIBRARIES
# =====================================================
import requests
# Pandas is the main tool we'll use to load and manipulate the Airbnb dataset
import pandas as pd

# Dash is the framework that lets us build an interactive web dashboard using Python
import dash

# These are Dash UI components.
# - dcc contains things like dropdowns, graphs, tabs
# - html lets us create HTML elements like Divs, headers, etc.
# - dash_table lets us render a data table in the dashboard
from dash import dcc, html, dash_table

# Dash callbacks use Input and Output to connect filters to charts.
# When an input changes (like a dropdown), the output charts update automatically.
from dash.dependencies import Input, Output

# Plotly Express is the quick way to build charts
import plotly.express as px

# Plotly Graph Objects gives more control when we need custom charts
import plotly.graph_objects as go

# These visualization libraries are commonly used in data analysis
# (they are not heavily used in this script but are available if needed)
import seaborn as sns
import matplotlib.pyplot as plt

# These are sometimes used for image handling in dashboards
import io
import base64

# Numpy is useful for numerical operations and arrays
import numpy as np


class AirbnbAnalytics:
    """
    A class to handle additional analytics and visualizations
    for the Airbnb dashboard, including:
    - Matplotlib histogram
    - Seaborn boxplot
    - External API for currency conversion (USD to SGD)
    """

    def __init__(self, df):
        self.df = df.copy()

    # -----------------------------
    # REST API: USD to SGD
    # -----------------------------
    def get_sgd_to_php_rate(self):
        try:
            # Marketshost provides free currency conversion JSON API
            url = "https://www.marketshost.com/production/api/rates.php"
            params = {"from": "SGD", "to": "PHP"}
            response = requests.get(url, params=params)
            data = response.json()

            # The API returns a structure like:
            # {
            #   "success": true,
            #   "query": {...},
            #   "result": {"rate": 46.12, ...}
            # }
            rate = data.get("result", {}).get("rate", None)

            # Fallback if API structure is different
            if rate is None:
                raise ValueError("Rate field missing")

            return rate

        except Exception as e:
            print("Error fetching SGD→PHP rate:", e)
            return 0  # fallback

    # -----------------------------
    # Matplotlib Histogram
    # -----------------------------
    def plot_price_histogram(self):
        fig = px.histogram(
            self.df,
            x="price",
            nbins=30,
            labels={"price": "Price"},
            color_discrete_sequence=["#FF5A5F"]
        )
        fig.update_layout(
            xaxis_title="Price",
            yaxis_title="Frequency",
            bargap=0.1
        )
        return fig

    # -----------------------------
    # Seaborn Boxplot
    # -----------------------------
    def plot_price_by_room(self):
        fig = px.box(
            self.df,
            x="room_type",
            y="price",
            color="room_type",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_layout(
            xaxis_title="Room Type",
            yaxis_title="Price",
            showlegend=False
        )
        return fig

# =====================================================
# 2. DATA LOADER CLASS
# =====================================================

# This class is responsible for loading the Airbnb dataset
# and doing the basic cleaning so the dashboard can use it.
class AirbnbDataLoader:

    # When we create this class we pass the file path
    # Example: AirbnbDataLoader("SG_listings.csv")
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None  # We'll store the dataframe here after loading

    # -------------------------------------------------
    # Load the CSV dataset
    # -------------------------------------------------
    def load_data(self):

        try:
            # Read the CSV file into a pandas dataframe
            self.df = pd.read_csv(self.file_path)

            # Helpful message so we know loading worked
            print("Dataset loaded successfully")

        except Exception as e:
            # If something goes wrong (wrong file path, bad file etc.)
            print("Error loading dataset:", e)

        return self.df


    # -------------------------------------------------
    # Clean and prepare the dataset
    # -------------------------------------------------
    def clean_data(self):

        # Work on a copy so we don't accidentally modify the raw dataframe
        df = self.df.copy()

        # The price column contains values like "$120" or "$1,200"
        # These symbols prevent numeric calculations.
        # So we remove "$" and "," using regex.
        df["price"] = df["price"].replace("[$,]", "", regex=True)

        # Convert the cleaned price column into a numeric type
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

        # The dataset already has a rating column called review_scores_rating
        # but it's a long name, so we create a simpler column called "rating"
        df["rating"] = df["review_scores_rating"]

        # Convert the last_review column into an actual datetime value
        review_date = pd.to_datetime(df["last_review"], errors="coerce")

        # From that date we extract useful time features
        df["year"] = review_date.dt.year
        df["month"] = review_date.dt.month
        df["month_name"] = review_date.dt.strftime("%B")

        # Some rows may not have price or location information.
        # Those rows aren't useful for maps or pricing analysis,
        # so we remove them.
        df = df.dropna(subset=["price", "latitude", "longitude"])

        # Save cleaned dataframe back to the class
        self.df = df

        return df

# =====================================================
# 3. CUSTOM FUNCTIONS
# =====================================================

# This function summarizes important metrics for each room type.
# For example:
# - average bathrooms
# - average bedrooms
# - median price
def room_type_metrics(data):

    metrics = data.groupby("room_type").agg({

        # Average number of bathrooms
        "bathrooms":"mean",

        # Average number of guests the property can host
        "accommodates":"mean",

        # Average number of bedrooms
        "bedrooms":"mean",

        # Average number of beds
        "beds":"mean",

        # Median price is used instead of mean because
        # Airbnb prices can have extreme outliers
        "price":"median"

    }).reset_index()

    return metrics


# This function estimates potential yearly revenue for listings.
# It's a rough estimate assuming the property is booked every day.
def calculate_estimated_revenue(data):

    revenue = 0

    # Loop through every listing price
    for price in data["price"]:

        # Ignore missing values
        if pd.notnull(price):

            # Estimate revenue assuming 365 booked nights
            yearly_revenue = price * 365

            revenue += yearly_revenue

    return revenue


# =====================================================
# 4. LOAD DATA
# =====================================================

# Create the data loader and point it to our dataset
loader = AirbnbDataLoader("SG_listings.csv")

# Load the dataset
df = loader.load_data()

# Run the cleaning steps we defined earlier
df = loader.clean_data()


# =====================================================
# 5. COLORS
# =====================================================

# Define some colors so the dashboard has a consistent style

# Airbnb's main red color
AIRBNB_RED = "#FF5A5F"

# Dark background used for chart panels
DARK_PANEL = "#111111"

# Light background used for cards
CARD_BG = "#F2F2F2"


# =====================================================
# 6. KPI VALUES
# =====================================================

# Calculate the average number of days listings are available
avg_availability = df["availability_365"].mean()

# From that we estimate utilization (how many days listings are booked)
# Example:
# If average availability = 200 days
# then approx booked days = 165
utilization = 365 - avg_availability


# =====================================================
# 7. DASH APP
# =====================================================

# Create the Dash app instance
# This basically initializes the web application
app = dash.Dash(__name__)
server = app.server
# -----------------------------------------------------
# Custom HTML template
# -----------------------------------------------------
# Dash normally wraps apps in a fixed-width container.
# This custom template removes that restriction so the
# dashboard can stretch across the full browser width.
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>Airbnb Dashboard</title>
    {%favicon%}
    {%css%}
    <style>
        body {
            margin:0;
            padding:0;
        }
        .container {
            width:100% !important;
            max-width:none !important;
        }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
'''


# =====================================================
# 8. UI COMPONENTS
# =====================================================

# This function builds a reusable KPI card.
# Instead of repeating the same HTML structure everywhere,
# we create it once and reuse it across the dashboard.
def kpi_card(title, value):

    return html.Div(
        [
            html.H2(value),
            html.P(title)
        ],

        style={
            "background": CARD_BG,
            "borderRadius": "20px",
            "padding": "20px",
            "textAlign": "center",
            "flex": "1",
            "minWidth": "180px",
            "boxShadow": "0px 2px 5px rgba(0,0,0,0.2)"
        }
    )


# Smaller card used for detailed metrics
# (for example room attributes like beds or bathrooms)
def detail_card(title, value):

    return html.Div(
        [
            html.H3(f"{value:.0f}", style={"margin":"0"}),
            html.P(title, style={"margin":"0","fontSize":"12px"})
        ],

        style={
            "background":"#ffffff",
            "borderRadius":"10px",
            "padding":"10px",
            "textAlign":"center",
            "minWidth":"120px",
            "boxShadow":"0px 1px 3px rgba(0,0,0,0.2)"
        }
    )


# Panel component that wraps every chart.
# It provides consistent styling so all charts look the same.
def panel(title, graph_id, height=None):

    style = {
        "background": DARK_PANEL,
        "borderRadius": "12px",
        "padding": "10px",
        "margin": "10px",
        "flex": 1,
        "display": "flex",
        "flexDirection": "column"
    }

    # Some panels need a fixed height (especially stacked charts)
    if height:
        style["height"] = height

    return html.Div(
        [
            html.H3(title, style={"color":"white"}),

            # The graph itself will be inserted here
            dcc.Graph(
                id=graph_id,
                config={"displayModeBar":False},
                style={"flex":1,"height":"100%"}
            )
        ],
        style=style
    )


# =====================================================
# 9. HEADER
# =====================================================

# This section builds the top banner of the dashboard.
# Think of it as the title bar that users see first when the page loads.
# It's mostly visual but important for branding and context.

header = html.Div(

    # The main title displayed at the top of the dashboard
    html.H1(
        "Airbnb Singapore Business Dashboard",
        style={"color":"white"}  # white text so it contrasts with the red background
    ),

    # Styling for the header container
    style={
        "backgroundColor":AIRBNB_RED,  # using the Airbnb brand color we defined earlier
        "padding":"20px",              # adds space inside the header
        "textAlign":"center"           # centers the title horizontally
    }
)


# =====================================================
# 10. FILTER CONTROLS
# =====================================================

# This section contains all the interactive filters.
# These dropdowns let users slice the dataset dynamically.
# Whenever a user changes one of these filters, the callback function
# later in the code will recompute the charts.

filters = html.Div([

    # -------------------------------------------------
    # Filter: Host Type
    # -------------------------------------------------
    # Airbnb distinguishes between superhosts and regular hosts.
    # This filter lets users analyze them separately.
    dcc.Dropdown(
        id="superhost_filter",

        options=[
            {"label":"All Hosts","value":"all"},
            {"label":"Superhost","value":"t"},
            {"label":"Regular Host","value":"f"}
        ],

        # Default selection when the dashboard first loads
        value="all"
    ),

    # -------------------------------------------------
    # Filter: Year
    # -------------------------------------------------
    # We dynamically generate the dropdown options from the dataset.
    # dropna() removes missing years
    # unique() gets distinct values
    # sorted() keeps them in order for a nicer UI
    dcc.Dropdown(
        id="year_filter",
        options=[{"label": y,"value": y} for y in sorted(df["year"].dropna().unique())],

        # multi=True means users can select multiple years at once
        multi=True,

        # Placeholder text shown before user selects anything
        placeholder="Year"
    ),

    # -------------------------------------------------
    # Filter: Month
    # -------------------------------------------------
    # Same idea as the year filter but using month names.
    dcc.Dropdown(
        id="month_filter",
        options=[{"label": m,"value": m} for m in sorted(df["month_name"].dropna().unique())],
        multi=True,
        placeholder="Month"
    ),

    # -------------------------------------------------
    # Filter: Room Type
    # -------------------------------------------------
    # Example room types:
    # - Entire home
    # - Private room
    # - Shared room
    dcc.Dropdown(
        id="room_filter",
        options=[{"label": r,"value": r} for r in df["room_type"].dropna().unique()],
        multi=True,
        placeholder="Room Type"
    ),

    # -------------------------------------------------
    # Filter: Neighbourhood
    # -------------------------------------------------
    # Allows geographic filtering within Singapore.
    dcc.Dropdown(
        id="neighbourhood_filter",
        options=[{"label": n,"value": n} for n in df["neighbourhood_cleansed"].dropna().unique()],
        multi=True,
        placeholder="Neighbourhood"
    ),

    # -------------------------------------------------
    # Filter: Specific Listing
    # -------------------------------------------------
    # This lets the user drill down to a specific Airbnb listing.
    # It’s mostly useful for deeper inspection.
    dcc.Dropdown(
        id="name_filter",
        options=[{"label": n,"value": n} for n in df["name"].dropna().unique()],
        multi=True,
        placeholder="Listing"
    )

],

# Layout styling for the filter section
style={
    # Grid layout makes filters align nicely in rows
    "display":"grid",

    # Creates 3 columns for filters
    "gridTemplateColumns":"repeat(3,1fr)",

    # Space between filters
    "gap":"10px",

    # Padding around the whole filter block
    "padding":"20px"
})


# =====================================================
# 11. DATA TABLE
# =====================================================

# This section builds a table that displays the raw dataset.
# It's useful for users who want to inspect the actual data
# behind the charts.

table = dash_table.DataTable(

    # Convert dataframe into a dictionary format Dash can read
    data=df.to_dict("records"),

    # Automatically create columns based on dataframe columns
    columns=[{"name": i,"id": i} for i in df.columns],

    # Only show 20 rows per page for performance
    page_size=20,

    # Table styling
    style_table={
        "height":"600px",   # fixed height
        "overflowY":"scroll" # vertical scroll if rows exceed height
    }
)


# =====================================================
# 12. DASHBOARD LAYOUT
# =====================================================

# This is the main structure of the entire dashboard.
# Everything we defined earlier (header, filters, charts)
# gets assembled here.

app.layout = html.Div([

    # Top banner
    header,

    # Filter controls just below the header
    filters,

    # Tabs allow us to split the dashboard into logical sections
    dcc.Tabs([

        # =====================================================
        # TAB 1 — OVERVIEW
        # =====================================================

        dcc.Tab(label="Overview", children=[

            # This is where the KPI cards will appear.
            # They are generated dynamically in the callback.
            html.Div(id="kpi_cards_div"),

            # Two-column layout under the KPI cards
            html.Div([

                # -------------------------------------------------
                # LEFT COLUMN
                # -------------------------------------------------
                # This column stacks three panels vertically.
                html.Div([

                    # Number of hosts chart
                    panel("Number of Host", "host_chart", height="300px"),

                    # Median pricing by room type
                    panel("Room Type Median Pricing", "room_chart", height="300px"),

                    # Gauge showing estimated occupancy
                    panel("Annual Occupancy (Booked Days)", "gauge_chart", height="300px"),
                ],

                # Column styling
                style={
                    "display":"flex",
                    "flexDirection":"column",
                    "gap":"10px",
                    "width":"33%",
                    "padding":"10px"
                }),

                # -------------------------------------------------
                # RIGHT COLUMN
                # -------------------------------------------------
                # This section contains the neighbourhood matrix.
                html.Div([

                    # Title for the neighbourhood section
                    html.H3("Neighbourhood Details", style={"color": AIRBNB_RED, "padding": "10px"}),

                    # Container where the matrix chart will be inserted
                    html.Div(
                        id="neighbourhood_matrix",

                        style={
                            "height": "910px",
                            "display": "flex",
                            "flexDirection": "column",
                            "backgroundColor": CARD_BG,
                            "borderRadius": "12px",
                            "boxShadow": "0px 2px 5px rgba(0,0,0,0.2)",
                            "padding": "10px"
                        }
                    )
                ],

                style={
                    "width":"67%",
                    "padding":"10px"
                })

            ],

            # Layout styling for the two columns
            style={
                "display":"flex",
                "gap":"20px",
                "padding":"10px"
            }),

        ]),


        # =====================================================
        # TAB 2 — PRICING ANALYTICS
        # =====================================================

        dcc.Tab(label="Pricing Analysis", children=[

            # Section title
            html.H3("Room Type Details", style={"padding":"20px"}),

            # Cards showing detailed metrics for each room type
            html.Div(
                id="room_details_cards",
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "gap": "20px",
                    "padding": "20px"
                }
            ),

            # Pricing charts layout
            html.Div([

                # Large neighbourhood pricing chart
                html.Div(
                    panel("Neighbourhood Pricing", "neighbourhood_chart", height="700px"),
                    style={"width": "33%", "display": "inline-block", "verticalAlign": "top"}
                ),

                # Right panel: Host, Room, and Property charts
                html.Div([
                    # Top row: Host Category + Room Type
                    html.Div([
                        html.Div(
                            panel("Host Category Pricing", "host_price_chart"),
                            style={"width": "50%", "display": "inline-block", "padding": "5px", "boxSizing": "border-box", "flex": 1}
                        ),
                        html.Div(
                            panel("Room Type Pricing", "room_chart_2"),
                            style={"width": "50%", "display": "inline-block", "padding": "5px", "boxSizing": "border-box", "flex": 1}
                        ),
                    ], style={"display": "flex", "gap": "10px", "flex": 1}),

                    # Bottom row: Property Type Pricing
                    html.Div(
                        panel("Property Type Pricing", "property_chart"),
                        style={"width": "100%", "padding": "5px", "boxSizing": "border-box", "flex": 1}
                    )

                ], style={
                    "width": "66%",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "10px",
                    "verticalAlign": "top",
                })

            ], style={"display": "flex", "gap": "10px"}),  # gap between left and right panels

            # Next row: histogram and boxplot
            html.Div([
                html.Div(
                    panel("Price Distribution", "histogram", height="350px"),
                    style={"width": "50%", "display": "inline-block", "padding": "10px", "boxSizing": "border-box"}
                ),

                html.Div(
                    panel("Price by Room Type", "boxplot", height="350px"),
                    style={"width": "50%", "display": "inline-block", "padding": "10px", "boxSizing": "border-box"}
                ),

            ], style={"display": "flex", "gap": "10px"})

        ], style={"height": "100%"}),


        # =====================================================
        # TAB 3 — RATINGS ANALYSIS
        # =====================================================

        dcc.Tab(label="Ratings Analysis", children=[

            # First row of charts
            html.Div([

                # Rating comparison between host types
                html.Div(
                    [
                        html.H3("Median Rating by Host", style={"color":"white", "marginBottom":"10px"}),
                        dcc.Graph(
                            id="host_rating_chart",
                            style={"flex":1, "height":"100%", "width":"100%"},
                            config={"displayModeBar": False}
                        )
                    ],

                    style={
                        "background": DARK_PANEL,
                        "borderRadius": "12px",
                        "padding": "10px",
                        "margin": "10px",
                        "flex": 1,
                        "display": "flex",
                        "flexDirection": "column"
                    }
                ),

                # Rating by room type
                html.Div(panel("Median Rating by Room Type","room_rating_chart", height="350px"),
                         style={"width":"50%","display":"inline-block","padding":"10px"})
            ],

            style={"display":"flex", "gap":"10px"}),

            # Second row of charts
            html.Div([

                # Ratings by geographic area
                html.Div(panel("Median Review per Area","rating_area_chart", height="350px"),
                         style={"width":"50%","display":"inline-block","padding":"10px"}),

                # Ratings trend over years
                html.Div(panel("Median Rating per Year","rating_chart", height="350px"),
                         style={"width":"50%","display":"inline-block","padding":"10px"}),

            ], style={"display":"flex", "gap":"10px"})
        ], style={"height":"100%"}),

        # =====================================================
        # TAB 4 — DATASET EXPLORER
        # =====================================================

        dcc.Tab(label="Dataset Explorer", children=[

            # Split view: map + table
            html.Div([

                # Map showing where listings are located
                html.Div([
                    dcc.Graph(id="map_chart")
                ], style={"width":"50%","display":"inline-block"}),

                # Raw dataset table
                html.Div([
                    table
                ], style={"width":"50%","display":"inline-block"})

            ])

        ], style={"height":"100%"})

    ], style={"flex":1})

],

# Global page styling
style={
    "fontFamily":"Arial",
    "backgroundColor":"#FAFAFA",
    "minHeight":"100vh",
    "width":"100%",
    "display":"flex",
    "flexDirection":"column"
})


# =====================================================
# 13. CALLBACK
# =====================================================

# This callback connects the dashboard filters (inputs)
# with all the charts, tables, and cards (outputs).
# In Dash, callbacks act like the "brain" of the dashboard.
# They listen for user interactions and update visual components accordingly.

# Every time the user changes a dropdown filter,
# this function runs again and refreshes the entire dashboard.
# Dash automatically detects the change and triggers this function.

@app.callback(
    [
        Output("room_chart","figure"),  # Room Type Median Pricing
        Output("room_chart_2","figure"), # Room Type Pricing
        Output("property_chart","figure"), # Property Type Pricing
        Output("host_chart","figure"), # Number of Host
        Output("rating_area_chart","figure"), # Median Review per Area
        Output("rating_chart","figure"), # Median Rating per Year
        Output("histogram","figure"), # Histogram
        Output("boxplot","figure"), # Boxplot
        Output("map_chart","figure"), # Mapp
        Output("gauge_chart","figure"), # Annual Occupancy (Booked Days)
        Output("kpi_cards_div","children"), # Kpi Cards Overview
        Output("room_details_cards","children"), # Room Type Details Cards
        Output("neighbourhood_chart","figure"), # Neighbourhood Pricing
        Output("host_price_chart","figure"),  # Host Category Pricing
        Output("neighbourhood_matrix", "children"), # Neighbourhood Details
        Output("host_rating_chart", "figure"), # Median Rating by Host
        Output("room_rating_chart", "figure"), # Median Rating by Room Type
    ],

    [
        # These inputs are the dashboard filters.
        # When a user changes any of them,
        # the callback automatically executes again.

        # For example:
        # If the user selects a specific year or room type,
        # Dash sends those values to the function parameters below.
        Input("superhost_filter","value"),
        Input("year_filter","value"),
        Input("month_filter","value"),
        Input("room_filter","value"),
        Input("neighbourhood_filter","value"),
        Input("name_filter","value")
    ]
)

def update_dashboard(superhost, year, month, room, neigh, name):
    # Start by copying the original dataframe.
    # We always work on a copy so the original dataset remains unchanged.
    # This prevents accidental modification of the raw data.
    dff = df.copy()

    # -------------------------------------------------
    # APPLY USER FILTERS
    # -------------------------------------------------
    # Each filter checks if the user selected something.
    # If so, the dataframe is filtered accordingly.

    # Example:
    # If the user chooses "Superhost",
    # we keep only rows where host_is_superhost == 't'.
    if superhost!="all":
        dff = dff[dff["host_is_superhost"]==superhost]

    # Filter dataset by selected years
    if year:
        dff = dff[dff["year"].isin(year)]

    # Filter dataset by selected months
    if month:
        dff = dff[dff["month_name"].isin(month)]

    # Filter by room types (Entire home, Private room, etc.)
    if room:
        dff = dff[dff["room_type"].isin(room)]

    # Filter by neighbourhood
    if neigh:
        dff = dff[dff["neighbourhood_cleansed"].isin(neigh)]

    # Filter by listing name
    if name:
        dff = dff[dff["name"].isin(name)]

    # Initialize analytics class with filtered dataframe
    analytics = AirbnbAnalytics(dff)

    # Matplotlib and Seaborn figures
    fig_histogram = analytics.plot_price_histogram()
    fig_boxplot = analytics.plot_price_by_room()

    # Get PHP/SGD exchange rate for KPI card
    sgd_to_php_rate = analytics.get_sgd_to_php_rate()

    # After this section, "dff" represents the filtered dataset
    # based on the user's selections.
    # All charts and KPIs will now be computed using this filtered data.

    # -------------------------------------------------
    # KPI METRICS
    # -------------------------------------------------
    # These numbers appear at the top of the dashboard
    # and summarize the filtered dataset.
    # They give users a quick overview before analyzing charts.
    total_listings = len(dff)

    # Median price gives a better representation than mean
    # because Airbnb prices often contain extreme outliers.
    # Median reduces the impact of very expensive listings.
    median_price = dff["price"].median() if not dff.empty else 0

    # Total number of reviews across all listings
    total_reviews = dff["number_of_reviews"].sum()

    # Median rating score across listings
    median_rating = dff["rating"].median() if not dff.empty else 0

    # Estimated revenue assuming full-year occupancy
    # This uses a custom function defined earlier.
    est_revenue = calculate_estimated_revenue(dff)

    # -------------------------------------------------
    # HOST CATEGORY PREPARATION
    # -------------------------------------------------
    # The dataset stores host type as:
    # t = superhost
    # f = regular host
    # Here we convert those codes into readable labels
    # so they are easier to display in charts.
    dff['host_label'] = dff['host_is_superhost'].fillna('null').replace({
        't': 'Superhost',
        'f': 'Regular host',
        'null': 'Unidentified'
    })

    # Count how many listings fall into each host category
    # This will later be used in a pie chart.
    host_counts = dff['host_label'].value_counts().reset_index()
    host_counts.columns = ['Host Type', 'Count']

    # -------------------------------------------------
    # HOST DISTRIBUTION PIE CHART
    # -------------------------------------------------
    # This chart shows the proportion of listings
    # owned by superhosts vs regular hosts.
    # It helps users understand host dominance in the market.
    fig_host = px.pie(
        dff,
        names="host_label",
        hole=0.6,
        color="host_label",
        color_discrete_map={
            'Superhost': AIRBNB_RED,
            'Regular host': '#00BFFF',
            'Unidentified': '#A9A9A9'
        }
    )

    # Improve visual readability
    # Percentages are displayed inside the donut slices.
    fig_host.update_traces(
        textposition='inside',
        textinfo='percent',
        pull=[0.05, 0.05, 0.05]
    )

    # Layout adjustments for spacing and appearance
    fig_host.update_layout(
        showlegend=True,
        margin=dict(l=5, r=5, t=30, b=5),
        height=500
    )

    # -------------------------------------------------
    # ROOM TYPE PRICING
    # -------------------------------------------------
    # First chart: median price per room type
    # This shows how expensive each room category typically is.
    room_price = dff.groupby("room_type")["price"].median().reset_index()
    fig_room = px.bar(
        room_price,
        x="room_type",
        y="price",
        color="room_type"
    )

    # Second chart: total price per room type
    # (useful for understanding revenue concentration)
    # For example, even if a room type is cheap,
    # there might be many listings generating large total revenue.
    sum_room_price = dff.groupby("room_type")["price"].sum().reset_index()
    fig_room_sum = px.bar(
        sum_room_price,
        x="room_type",
        y="price",
        color="room_type"
    )
    fig_room2 = fig_room_sum


    # -------------------------------------------------
    # NEIGHBOURHOOD PRICING
    # -------------------------------------------------
    # This chart ranks neighbourhoods by total listing price.
    # It helps identify which areas generate the most value.
    neighbourhood_price = dff.groupby("neighbourhood_cleansed")["price"].sum().reset_index()

    fig_neighbourhood = px.bar(
        neighbourhood_price,
        y="neighbourhood_cleansed",
        x="price",
        text="price",
        orientation="h"
    )

    # -------------------------------------------------
    # HOST CATEGORY PRICING
    # -------------------------------------------------
    # This compares total pricing between superhosts
    # and regular hosts to see which group dominates pricing.
    host_price = dff.groupby("host_is_superhost")["price"].sum().reset_index()

    # Map t/f to readable labels
    host_price["host_is_superhost"] = host_price["host_is_superhost"].map({
        "t": "Superhost",
        "f": "Regular Host"
    })

    # Create single bar per host type
    fig_host_price = px.bar(
        host_price,
        x="host_is_superhost",
        y="price",
        text="price",  # show total price on top
        color_discrete_sequence=[AIRBNB_RED]  # single color
    )

    fig_host_price.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')

    fig_host_price.update_layout(
       # title="Host Category Pricing (Total Price)",
        xaxis_title="Host Type",
        yaxis_title="Total Price",
        margin=dict(t=50, b=50, l=50, r=50),
        showlegend=False
    )

    # -------------------------------------------------
    # PROPERTY TYPE PRICING
    # -------------------------------------------------
    # This shows total price aggregated by property type
    # such as apartments, houses, condos, etc.
    property_price_total = dff.groupby("property_type")["price"].sum().reset_index()

    # Create clustered column chart (single bar per property type)
    fig_property = px.bar(
        property_price_total,
        x="property_type",      # horizontal axis
        y="price",              # vertical axis = total price
        text="price",           # show total price on top
        color="property_type"   # keep distinct colors per property type
    )

    # Show price on top of each bar in currency format
    fig_property.update_traces(
        texttemplate='¥%{text:,.0f}',
        textposition='outside'
    )

    # Adjust layout
    fig_property.update_layout(
        xaxis_title="Property Type",
        yaxis_title="Total Price",
        xaxis_tickangle=-30,
        margin=dict(t=50, b=150, l=50, r=50),
        height=500,
        showlegend=False
    )

    # Room Type Median Pricing
    # Show price on top of each bar in currency format
    fig_room2.update_traces(
        texttemplate='$%{y:,.0f}',
        textposition='outside'
    )

    fig_room2.update_layout(
        barmode='group',
        xaxis_title="Room Type",
        yaxis_title="Total Price",
        showlegend=False,
        margin=dict(t=50, b=50, l=50, r=50)
    )

    # -------------------------------------------------
    # RATING TREND
    # -------------------------------------------------
    # Shows how median ratings change across years.
    # Useful for understanding long-term customer satisfaction.
    rating_year = dff.groupby("year")["rating"].median().reset_index()

    fig_rating = px.line(
        rating_year,
        x="year",
        y="rating",
        text="rating",
        markers=True
    )

    # -------------------------------------------------
    # Annual Occupancy (Booked Days)
    # -------------------------------------------------
    # Calculates estimated booked days per year.
    # Airbnb dataset provides availability_365
    # which means how many days the listing is still available.

    # So:
    # Occupied days = 365 - available days
    util = 365 - dff["availability_365"].mean()

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=util,
            gauge={
                "axis": {
                    "range": [0, 365],
                    "tickvals": [0, 365*0.25, 365*0.5, 365*0.75, 365],  # force ticks
                    "ticktext": ['0', str(int(365*0.25)), str(int(365*0.5)), str(int(365*0.75)), '365']
                },
                "bar": {"color": AIRBNB_RED}
            }
        )
    )

    # Group by host type and calculate median rating
    host_rating = dff.groupby("host_is_superhost")["rating"].median().reset_index()

    # Map t/f to readable labels
    host_rating["host_is_superhost"] = host_rating["host_is_superhost"].map({
        "t": "Superhost",
        "f": "Regular Host"
    })

    # Create Pie Chart
    fig_host_rating = px.pie(
        host_rating,
        names="host_is_superhost",
        values="rating",
        color="host_is_superhost",
        color_discrete_map={"Superhost": "green", "Regular Host": "blue"}
    )

    # Fill panel dynamically
    fig_host_rating.update_traces(
        textinfo='label+percent+value',
        textfont_size=16,
        pull=[0.05, 0.05]
    )

    fig_host_rating.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        autosize=True
    )

    # 2️⃣ Median Rating by Room Type
    room_rating = dff.groupby("room_type")["rating"].median().reset_index()
    fig_room_rating = px.bar(
        room_rating,
        x="room_type",
        y="rating",
        color="room_type",
        text="rating",
        title="Median Rating by Room Type",
    )
    fig_room_rating.update_layout(barmode="stack", showlegend=False)

    # Median Review per Area (aggregate across all room types)
    rating_area = dff.groupby("neighbourhood_cleansed")["rating"].median().reset_index()

    fig_rating_area = px.bar(
        rating_area,
        x="neighbourhood_cleansed",
        y="rating",
        color_discrete_sequence=[AIRBNB_RED]  # single color for all bars
    )

    fig_rating_area.update_layout(
        title="Median Review per Area",
        xaxis_title="Neighbourhood",
        yaxis_title="Median Rating",
        margin=dict(t=50, b=100, l=50, r=50),  # adjust for label readability
        xaxis_tickangle=-45
    )

    # -------------------------------------------------
    # MAP VISUALIZATION
    # -------------------------------------------------
    # Displays listings geographically using latitude and longitude.
    # Larger markers represent higher aggregated price values.
    map_df = dff.dropna(subset=["latitude","longitude","price","room_type"])

    map_df = map_df.groupby(
        ["latitude","longitude","room_type"],
        as_index=False
    ).agg({"price":"sum"})

    fig_map = px.scatter_mapbox(
        map_df,
        lat="latitude",
        lon="longitude",
        size="price",
        color="room_type",
        size_max=50,
        zoom=10,
        mapbox_style="carto-positron",
        hover_data=["price","room_type"]
    )

    fig_map.update_layout(
        height=600,
        title="Total Price by Location"
    )

    # -------------------------------------------------
    # ROOM METRIC DETAIL CARDS
    # -------------------------------------------------
    # These cards show average room attributes
    # such as bedrooms, beds, bathrooms, and capacity
    # for each room type.
    metrics = room_type_metrics(dff)

    cards = []

    for _, row in metrics.iterrows():
        cards.append(
            html.Div([
                # Room type header
                html.H4(row["room_type"], style={"color": AIRBNB_RED, "marginBottom": "10px"}),

                # Inner detail cards
                html.Div([
                    html.Div(detail_card("Bedrooms", row["bedrooms"]), style={"flex": 1}),
                    html.Div(detail_card("Beds", row["beds"]), style={"flex": 1}),
                    html.Div(detail_card("Bathrooms", row["bathrooms"]), style={"flex": 1}),
                    html.Div(detail_card("Accommodates", row["accommodates"]), style={"flex": 1})
                ],
                style={
                    "display": "flex",
                    "gap": "5px",          # gap between inner cards
                    "justifyContent": "space-between",
                    "flexGrow": 1,          # expand to fill panel height
                    "width": "100%"
                })

            ],
            style={
                "border": "1px dashed #FF5A5F",
                "padding": "15px",
                "borderRadius": "5px",
                "background": "#F8F8F8",
                "width": "90%",
                "display": "flex",
                "flexDirection": "column",  # stack header + inner cards vertically
                "gap": "5px"               # gap between header and inner cards
            })
        )


    # --- Create Neighbourhood Details DataTable ---
    # This section builds a detailed table summarizing metrics for each neighbourhood.
    # It calculates estimated annual revenue, median rating, and total reviews
    # for every neighbourhood based on the filtered dataset.
    # 
    # Then it formats these numbers nicely:
    # - Revenue as a currency string (e.g., $1,234,567)
    # - Median Rating rounded to 2 decimals
    # - Reviews with commas for readability
    #
    # After that, it creates a Dash DataTable component (`neigh_table`) with:
    # - Native sorting and filtering enabled
    # - Dynamic page size based on panel height
    # - Styling for headers, rows, and alternating row colors
    # 
    # This table will be displayed in the dashboard and is returned by the callback
    # so users can explore neighbourhood-level insights interactively.
    neigh_grouped = dff.groupby("neighbourhood_cleansed").agg(
        est_annual_revenue = ("price", lambda x: x.sum() * 365),
        median_rating = ("rating", "median"),
        total_reviews = ("number_of_reviews", "sum")
    ).reset_index()

    neigh_grouped.fillna(0, inplace=True)

    # Format revenue as currency string
    neigh_grouped["Est. Annual Revenue"] = neigh_grouped["est_annual_revenue"].apply(lambda x: f"${int(x):,}")

    # Round Median Rating to 2 decimals
    neigh_grouped["Median Rating"] = neigh_grouped["median_rating"].round(2)

    # Format Reviews with commas
    neigh_grouped["Reviews"] = neigh_grouped["total_reviews"].astype(int).apply(lambda x: f"{x:,}")

    # Select and rename columns
    neigh_display_df = neigh_grouped[["neighbourhood_cleansed", "Est. Annual Revenue", "Median Rating", "Reviews"]]
    neigh_display_df = neigh_display_df.rename(columns={"neighbourhood_cleansed": "Neighbourhood"})

    # ===== DYNAMIC PAGE SIZE =====
    ROW_HEIGHT = 40               # height per row in px
    panel_height = 910            # height of the neighbourhood panel
    header_height = 50            # height of panel header (H3)
    available_height = panel_height - header_height
    dynamic_page_size = max(5, available_height // ROW_HEIGHT)  # at least 5 rows

    neigh_table = dash_table.DataTable(
        data=neigh_display_df.to_dict("records"),
        columns=[{"name": col, "id": col} for col in neigh_display_df.columns],
        sort_action="native",
        filter_action="native",
        page_size=dynamic_page_size,  # <-- dynamically calculated
        style_table={
            "flex": "1",
            "overflowY": "auto",
            "minWidth": "100%"
        },
        style_cell={
            "textAlign": "left",
            "padding": "5px",
            "fontFamily": "Arial",
            "fontSize": "14px",
            "minWidth": "120px",
            "width": "auto"
        },
        style_header={
            "backgroundColor": AIRBNB_RED,
            "fontWeight": "bold",
            "color": "white"
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)"
            }
        ]
    )

    # -------------------------------------------------
    # KPI CARDS
    # -------------------------------------------------
    # These appear at the very top of the dashboard
    # and summarize the filtered dataset.
    est_revenue_php = est_revenue * sgd_to_php_rate
    kpi_cards = html.Div([
        kpi_card("Listings", f"{total_listings:,}"),
        kpi_card("Est Revenue (SGD)", f"${est_revenue:,.0f}"),
        kpi_card("Est Revenue (PHP)", f"₱{est_revenue_php:,.0f}"),
        kpi_card("Median Price", f"${median_price:,.0f}"),
        kpi_card("Reviews", f"{total_reviews:,}"),
        kpi_card("Median Rating", f"{median_rating:.2f}")
    ], style={
            "display": "flex",
            "flexWrap": "nowrap",
            "gap": "20px",
            "padding": "20px"
    })

    # -------------------------------------------------
    # RETURN RESULTS
    # -------------------------------------------------
    # The order of returned values must exactly match
    # the order of outputs defined at the top of the callback.
    # If the order is incorrect, Dash will throw an error.
    return (
        fig_room,
        fig_room2,
        fig_property,
        fig_host,
        fig_rating_area,
        fig_rating,
        fig_histogram,
        fig_boxplot,
        fig_map,
        fig_gauge,
        kpi_cards,
        cards,
        fig_neighbourhood,
        fig_host_price,
        neigh_table,
        fig_host_rating,
        fig_room_rating
    )


# =====================================================
# 14. RUN SERVER
# =====================================================

# This starts the Dash web server so the dashboard
# can be viewed in a browser.
# When this file is executed, Dash launches a local server
if __name__ == "__main__":
    app.run_server(debug=False)




