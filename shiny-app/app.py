from shiny import App, render, ui
import pandas as pd
import geopandas as gpd
import plotly.express as px

# Load the dataset
csv_file_path = "/Users/guillerminamarto/Documents/GitHub/Final_Project/data/shiny_ready_data.csv"
final_data = pd.read_csv(csv_file_path)
final_data["category"] = final_data["category"].fillna("Unknown").astype(str)

# Load the shapefile as a GeoDataFrame
shapefile_path = "/Users/guillerminamarto/Documents/GitHub/Final_Project/data/cultural_shp/cultural_shapefile.shp"
cultural_gdf = gpd.read_file(shapefile_path)

# Ensure required columns exist
required_columns = ["latitude", "longitude", "province", "departme_1", "category"]
missing_columns = [col for col in required_columns if col not in cultural_gdf.columns]
if missing_columns:
    raise ValueError(f"The shapefile is missing the following required columns: {', '.join(missing_columns)}")

# Define the UI layout
app_ui = ui.page_fluid(
    ui.tags.style("""
        .custom-card { 
            background-color: #f9f9f9; 
            border: 1px solid #ddd; 
            border-radius: 5px; 
            padding: 15px; 
            text-align: center; 
            font-size: 18px; 
            font-weight: bold; 
            margin-bottom: 10px;
        }
        .custom-card span {
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }
        .app-title {
            text-align: center;
            font-size: 28px; 
            font-weight: bold; 
            margin-top: 20px;
            margin-bottom: 40px;
        }
        .section-title {
            font-size: 22px;
            font-weight: bold;
            margin-top: 30px;
            margin-bottom: 15px;
        }
    """),
    ui.h2("Cultural Spaces and Attendance Rates", class_="app-title"),
    ui.row(
        ui.column(6,  # Left side: Cards and bar chart
            ui.h3("Cultural Spaces by Category", class_="section-title"),
            ui.row(
                *[
                    ui.column(4, ui.div(ui.output_ui(f"{category.replace(' ', '_')}_card"), class_="custom-card"))
                    for category in final_data["category"].unique() if category != "Unknown"
                ]
            ),
            ui.h3("School Attendance Rates by Age Group", class_="section-title"),
            ui.output_image("bar_chart")
        ),
        ui.column(6,  # Right side: Dynamic map and dropdowns
            ui.h3("Filter Options", class_="section-title"),
            ui.input_select("province", "Select a Province",
                            ["Total Country"] + cultural_gdf["province"].dropna().unique().tolist()),
            ui.output_ui("department"),
            ui.h3("Map of Cultural Spaces by Category", class_="section-title"),
            ui.output_image("dynamic_map")
        )
    )
)

# Define the server logic
def server(input, output, session):
    # Dynamic department dropdown
    @output
    @render.ui
    def department():
        if input.province() == "Total Country":
            return ui.input_select("department", "Select a Department", ["Total Province"])
        else:
            filtered_depts = cultural_gdf.loc[cultural_gdf["province"] == input.province(), "departme_1"]
            if filtered_depts.empty:
                return ui.input_select("department", "Select a Department", ["No Departments Found"])
            return ui.input_select(
                "department", "Select a Department",
                ["Total Province"] + filtered_depts.dropna().unique().tolist()
            )

    # Generate cards for each category
    for category in final_data["category"].unique():
        if category != "Unknown":
            @output(id=f"{category.replace(' ', '_')}_card")
            @render.ui
            def _(category=category):
                filtered_data = cultural_gdf
                if input.province() != "Total Country":
                    filtered_data = filtered_data[filtered_data["province"] == input.province()]
                if input.department() and input.department() != "Total Province":
                    filtered_data = filtered_data[
                        (filtered_data["province"] == input.province()) &
                        (filtered_data["departme_1"] == input.department())
                    ]
                count = filtered_data[filtered_data["category"] == category].shape[0]
                return ui.tags.div(
                    ui.tags.b(f"{category}:"),
                    ui.tags.br(),
                    ui.tags.span(f"{int(count)}")
                )

    # Render bar chart as image (uses `final_data`)
    @output
    @render.image
    def bar_chart():
        filtered_data = final_data
        if input.province() != "Total Country":
            filtered_data = filtered_data[filtered_data["province"] == input.province()]
        if input.department() and input.department() != "Total Province":
            filtered_data = filtered_data[
                (filtered_data["province"] == input.province()) &
                (filtered_data["department"] == input.department())
            ]

        attendance_data = filtered_data[["4 to 5 years", "6 to 11 years", "12 to 14 years", "15 to 17 years", "avg attendance rate"]].mean()

        fig = px.bar(
            x=attendance_data.index,
            y=attendance_data.values / 100,
            labels={"x": "Age Group", "y": "Attendance Rate (%)"},
            color=attendance_data.values,
            color_continuous_scale="Blues",
        )
        fig.update_layout(
            xaxis_title="Age Group",
            yaxis_title="Attendance Rate (%)",
            plot_bgcolor="white",
            font=dict(size=14),
            showlegend=False,
        )
        fig.update_traces(texttemplate='%{y:.1%}', textposition='outside')

        # Save the chart to a file
        img_path = "/tmp/bar_chart.png"
        fig.write_image(img_path)
        return {"src": img_path, "alt": "School Attendance Rates Bar Chart"}

    # Render the dynamic map
    @output
    @render.image
    def dynamic_map():
        filtered_data = cultural_gdf
        if input.province() != "Total Country":
            filtered_data = filtered_data[filtered_data["province"] == input.province()]
        if input.department() and input.department() != "Total Province":
            filtered_data = filtered_data[
                (filtered_data["province"] == input.province()) &
                (filtered_data["departme_1"] == input.department())
            ]

        center_lat, center_lon = -40, -80  # Center coordinates
        fig = px.scatter_mapbox(
            filtered_data,
            lat="latitude",
            lon="longitude",
            color="category",
            hover_name="category",
            hover_data={"province": True, "departme_1": True},
            mapbox_style="carto-positron",
            zoom=2.7,
            center={"lat": center_lat, "lon": center_lon},
        )
        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            mapbox_bounds={"west": -85, "east": -30, "south": -75, "north": 0},
        )

        # Save the map to a file
        map_path = "/tmp/dynamic_map.png"
        fig.write_image(map_path)
        return {"src": map_path, "alt": "Dynamic Map of Cultural Spaces"}

# Create the app
app = App(app_ui, server)

if __name__ == "__main__":
    app.run()
