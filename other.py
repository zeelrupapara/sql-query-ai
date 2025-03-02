def add_message_to_history(role, content, visualization=None):
    """Add message to chat history with visualization data and settings."""
    current_user = st.session_state.get('current_user')
    if current_user:
        # If visualization exists, store the current chart settings
        if visualization:
            viz_settings = {
                'chart_type': st.session_state.get('current_chart_type', 'bar'),
                'x_col': st.session_state.get('current_x_col'),
                'y_col': st.session_state.get('current_y_col'),
                'data': visualization  # Store the complete visualization data
            }
        else:
            viz_settings = None

        message = {
            "role": role,
            "content": content,
            "visualization": viz_settings,
            "timestamp": datetime.now().isoformat()
        }
        
        # Initialize list if it doesn't exist
        if current_user not in st.session_state['user_chat_histories']:
            st.session_state['user_chat_histories'][current_user] = []
            
        st.session_state['user_chat_histories'][current_user].append(message)

def create_static_visualization(viz_settings):
    """Create a visualization without interactive elements."""
    if not viz_settings or not viz_settings.get('data'):
        return None

    try:
        # Get data and settings
        data = viz_settings['data'].get('data', [])
        if not data:
            return None
            
        chart_type = viz_settings.get('chart_type', 'bar')
        x_col = viz_settings.get('x_col')
        y_col = viz_settings.get('y_col')
        
        # If columns not specified, try to get from default settings
        if not x_col or not y_col:
            default_settings = viz_settings['data'].get('default_settings', {})
            x_col = default_settings.get('x_col')
            y_col = default_settings.get('y_col')
            
        if not x_col or not y_col:
            return None

        # Convert data to DataFrame and ensure column types
        df = pd.DataFrame(data)
        
        # Apply the same styling as create_visualization
        return create_visualization(df, chart_type, x_col, y_col)
        
    except Exception as e:
        st.error(f"Error creating static visualization: {e}")
        return None

def create_visualization(data, chart_type, x_col, y_col):
    """Create an Altair visualization based on the selected parameters."""
    try:
        # Convert data to DataFrame
        df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame(data)

        # Color scheme
        color_scheme = 'tableau10'  # Professional color palette
        
        # Basic chart configuration with improved styling
        base_config = {
            "width": 600,
            "height": 400,
        }

        # Common encoding configurations
        tooltip_config = [
            alt.Tooltip(x_col, title=x_col.replace('_', ' ').title()),
            alt.Tooltip(y_col, title=y_col.replace('_', ' ').title(), format=',.0f')
        ]

        if chart_type == "bar":
            chart = alt.Chart(df, **base_config).mark_bar(
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
                opacity=0.8,
                width=20  # Adjust bar width
            ).encode(
                x=alt.X(x_col, 
                       sort='-y',
                       axis=alt.Axis(labelAngle=-45, labelOverlap=True)),
                y=alt.Y(y_col,
                       scale=alt.Scale(zero=True),
                       axis=alt.Axis(grid=True, gridOpacity=0.3)),
                color=alt.Color(y_col, scale=alt.Scale(scheme=color_scheme)),
                tooltip=tooltip_config
            ).properties(
                title=alt.TitleParams(
                    f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
                    fontSize=16,
                    anchor='middle'
                )
            )
            
        elif chart_type == "line":
            chart = alt.Chart(df, **base_config).mark_line(
                point=True,
                strokeWidth=3,
                opacity=0.8
            ).encode(
                x=alt.X(x_col, axis=alt.Axis(labelAngle=-45)),
                y=alt.Y(y_col, 
                       scale=alt.Scale(zero=False),
                       axis=alt.Axis(grid=True, gridOpacity=0.3)),
                color=alt.value('#1f77b4'),  # Professional blue color
                tooltip=tooltip_config
            ).properties(
                title=alt.TitleParams(
                    f"Trend of {y_col.replace('_', ' ').title()} over {x_col.replace('_', ' ').title()}",
                    fontSize=16,
                    anchor='middle'
                )
            )
            
        elif chart_type == "scatter":
            chart = alt.Chart(df, **base_config).mark_circle(
                size=100,
                opacity=0.6
            ).encode(
                x=alt.X(x_col, scale=alt.Scale(zero=False)),
                y=alt.Y(y_col, scale=alt.Scale(zero=False)),
                color=alt.Color(y_col, scale=alt.Scale(scheme=color_scheme)),
                size=alt.value(100),
                tooltip=tooltip_config
            ).properties(
                title=alt.TitleParams(
                    f"{y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}",
                    fontSize=16,
                    anchor='middle'
                )
            )
            
        elif chart_type == "heatmap":
            chart = alt.Chart(df, **base_config).mark_rect().encode(
                x=alt.X(x_col, axis=alt.Axis(labelAngle=-45)),
                y=alt.Y(y_col),
                color=alt.Color('count()',
                              scale=alt.Scale(scheme='viridis'),
                              legend=alt.Legend(title='Count')),
                tooltip=[
                    alt.Tooltip(x_col),
                    alt.Tooltip(y_col),
                    alt.Tooltip('count()', title='Count')
                ]
            ).properties(
                title=alt.TitleParams(
                    f"Heatmap of {y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}",
                    fontSize=16,
                    anchor='middle'
                )
            )

        # Add a configuration to make the chart more professional
        chart = chart.configure_axis(
            gridColor='#f0f0f0',
            domainColor='#cccccc',
            tickColor='#cccccc',
            labelFontSize=12,
            titleFontSize=14
        ).configure_title(
            fontSize=16,
            font='Arial',
            anchor='middle',
            color='#333333'
        ).configure_view(
            strokeWidth=0
        )

        return chart
    except Exception as e:
        st.error(f"Error creating visualization: {e}")
        return None

def show_visualization_options(response, key_prefix):
    """Handle visualization options and display for new messages only."""
    if not response.get('visualization'):
        return

    viz_data = response['visualization']
    
    try:
        df = pd.DataFrame(viz_data['data'])
        
        # Ensure numeric and categorical columns are properly identified
        numeric_types = ['int64', 'float64']
        object_types = ['object', 'string']
        
        numeric_cols = df.select_dtypes(numeric_types).columns.tolist()
        categorical_cols = df.select_dtypes(object_types).columns.tolist()
        
        # Update visualization data
        viz_data.update({
            'numeric_columns': numeric_cols,
            'categorical_columns': categorical_cols
        })
        
        # Create visualization
        if numeric_cols and (categorical_cols or numeric_cols):
            chart = create_visualization(
                viz_data['data'],
                st.session_state.get('current_chart_type', 'bar'),
                categorical_cols[0] if categorical_cols else numeric_cols[0],
                numeric_cols[0]
            )
            if chart:
                st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("No Visualization Needed")
            
    except Exception as e:
        st.error(f"Error in visualization options: {e}")

def handle_cached_response(cached_response):
    """Handle cached response with proper visualization."""
    if cached_response and 'visualization' in cached_response:
        try:
            # Convert cached data back to proper format
            df = pd.DataFrame(cached_response['visualization']['data'])
            
            # Update visualization data with proper column types
            numeric_types = ['int64', 'float64']
            object_types = ['object', 'string']
            
            numeric_cols = df.select_dtypes(['int64', 'float64']).columns.tolist()
            categorical_cols = df.select_dtypes(['object', 'string']).columns.tolist()
            
            cached_response['visualization'].update({
                'numeric_columns': numeric_cols,
                'categorical_columns': categorical_cols
            })
            
            # Add to chat history and display
            handle_response(cached_response)
            return True
        except Exception as e:
            st.error(f"Error processing cached response: {e}")
            return False
    return False

def handle_response(response):
    """Handle the response and visualization creation."""
    sql_query = response.get('sql_query')
    summary = response.get('summary', 'No summary available.')
    visualization = response.get('visualization')
    follow_up_questions = response.get('follow_up_questions')
    
    # Format the content based on what's available
    content = ""
    if sql_query:
        content += f"SQL Query: {sql_query}\n\n"
    content += f"Summary: {summary}"
    
    # Add to chat history with visualization
    add_message_to_history("assistant", content, visualization)
    
    with st.chat_message("assistant"):
        if sql_query and sql_query.startswith("PRAGMA"):
            st.markdown(summary)
        else:
            st.markdown(summary)
            if visualization:
                show_visualization_options(response, f"viz_{datetime.now().isoformat()}")
        if follow_up_questions:
            st.markdown("Follow-up questions:")
            for question in follow_up_questions:
                st.markdown(f"- {question}")

def handle_csv_or_excel_upload(uploaded_file):
    import tempfile
    import sqlite3
    import pandas as pd
    
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db_path = temp_db.name
    temp_db.close()

    # Read CSV or Excel into a DataFrame
    if uploaded_file.filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Write DataFrame to temporary SQLite DB
    conn = sqlite3.connect(temp_db_path)
    df.to_sql("uploaded_data", conn, if_exists="replace", index=False)
    conn.close()

    return temp_db_path

def handle_sql_upload(uploaded_file):
    import tempfile
    import sqlite3
    
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db_path = temp_db.name
    temp_db.close()
    
    try:
        # Read SQL file content
        sql_content = uploaded_file.getvalue().decode('utf-8')
        
        # Connect to the temporary database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Split and execute SQL statements
        # This handles both single and multiple statements
        sql_commands = sql_content.split(';')
        
        for command in sql_commands:
            command = command.strip()
            if command:  # Skip empty statements
                try:
                    cursor.execute(command)
                except sqlite3.Error as e:
                    st.warning(f"Skipping invalid SQL statement: {e}")
                    continue
        
        conn.commit()
        conn.close()
        return temp_db_path
        
    except Exception as e:
        st.error(f"Error processing SQL file: {e}")
        os.unlink(temp_db_path)  # Clean up the temporary file
        return None