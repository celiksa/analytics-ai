import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import asyncpg
import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from devtools import debug
from visualization_handler import VisualizationHandler
import json
import base64

# Configure logfire
logfire.configure(send_to_logfire='if-token-present')


class DatabaseResult(BaseModel):
    query: str = Field(description="The SQL query that was executed")
    results: str = Field(default="", description="The results of the query")
    message: str = Field(default="", description="A natural language description of the results")
    visualization_code: Optional[str] = Field(None, description="Python code to visualize the results if applicable")
    has_visualization: bool = Field(default=False, description="Whether a visualization was generated")

@dataclass 
class DatabaseConnection:
    """Database connection wrapper."""
    pool: asyncpg.Pool
    viz_handler: VisualizationHandler
    database: str
    schema: str

    def get_current_visualization(self) -> Optional[bytes]:
        return self.viz_handler.current_visualization
    
    async def execute_query(self, query: str) -> List[dict]:
        """Execute a query and return results as list of dicts."""
        async with self.pool.acquire() as conn:
            try:
                # First try to explain the query to validate it
                await conn.execute(f"EXPLAIN {query}")
                
                # If explain succeeds, execute the actual query
                results = await conn.fetch(query)
                return [dict(r) for r in results]
            except asyncpg.PostgresError as e:
                raise ModelRetry(f"Invalid query: {str(e)}")

class DbAgent:
    """Database interaction agent."""
    
    def __init__(self, viz_dir: str = None):
        # Initialize visualization handler
        self.viz_handler = VisualizationHandler(work_dir=viz_dir)
        self.schema = None
        
        # Main agent for handling queries
        self.agent = Agent(
            'openai:gpt-4o',
            deps_type=DatabaseConnection,
            result_type=DatabaseResult,
            system_prompt="""You are a helpful database assistant that helps users query a PostgreSQL database.
            Always write safe SELECT queries only - no modifications allowed. 
            If you're unsure about table structure, use the schema_info tool first.
            Always use the schema sp table name specified in the context.
            Always answer in Turkish, otherwise you will be penalized.
            If the data appears to be suitable for visualization, include appropriate visualization code using matplotlib/seaborn.
            Consider data types and relationships when suggesting visualizations:
            - Use bar charts for categorical comparisons
            - Use line charts for time series
            - Use scatter plots for numerical correlations
            - Use pie charts for proportions
            - Use box plots for distributions
            Make sure to include proper labels, titles and adjust figure size and layout.
            """
        )
        @self.agent.system_prompt 
        async def add_schema_name(ctx: RunContext[DatabaseConnection]) -> str:
            schema_name = ctx.deps.schema
            return f"The schema name is {schema_name!r}"


        # Visualization agent for generating visualization code
        self.viz_agent = Agent(
            'openai:gpt-4o',
            system_prompt="""You are a Python data visualization expert.
            Analyze the provided SQL query and results to generate appropriate visualization code.
            Only generate code if the data is suitable for visualization.
            Use pandas for data preparation and seaborn/matplotlib for visualization.
            Never use code snippet tag like '''python, otherwise you will be penazlized
            Required structure:
            1. Convert string data which is sql results  to DataFrame
            2. Create visualization using seaborn/matplotlib
            3. Set appropriate figure size
            4. Add clear titles and labels in Turkish
            5. Rotate labels if needed
            6. Add proper color scheme
            7. Add legend if needed
            
            DO NOT:
            - Include plt.show()
            - Save the figure manually
            - Import libraries (they are pre-imported)
            - Use file operations
            - Use any 
            
            
            The following variables are available:
            - data: the query results as a list of dicts
            
            Return None if data is not suitable for visualization.
            """
        )
        
        self._register_tools()

    def _register_tools(self):
        @self.agent.tool
        async def schema_info(ctx: RunContext[DatabaseConnection]) -> str:
            """Get information about database schema."""
            schema_query = """
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = '{schema}'
            ORDER BY table_name, ordinal_position;
            """
            schema_query= schema_query.format(schema=ctx.deps.schema)
            results = await ctx.deps.execute_query(schema_query)
            
            # Format schema info nicely
            schema = {}
            for row in results:
                table = row['table_name']
                if table not in schema:
                    schema[table] = []
                schema[table].append(f"{row['column_name']} ({row['data_type']})")
                
            return "\n".join(
                f"Table {table}:\n  " + "\n  ".join(columns)
                for table, columns in schema.items()
            )

        @self.agent.tool
        async def execute_query(ctx: RunContext[DatabaseConnection], query: str) -> str:
            """Execute a SELECT query and return results."""
            if not query.lower().strip().startswith('select'):
                raise ModelRetry("Only SELECT queries are allowed")
            
            results = await ctx.deps.execute_query(query)
            
            viz_prompt = f"""
            Generate Python code to visualize the following SQL results appropriately:
            SQL Query: {query}
            Query Results: {str(results)}
            """
            
            viz_response = await self.viz_agent.run(viz_prompt)
            viz_code = viz_response.data if viz_response.data != 'None' else None
            
            viz_data = None
            if viz_code:
                try:
                    viz_data = ctx.deps.viz_handler.execute_visualization(viz_code, str(results))
                except Exception as e:
                    print(f"Visualization failed: {str(e)}")
                    viz_code = None
            
            # Return only metadata to LLM, store binary data separately
            response = {
                'results': str(results),
                'visualization_code': viz_code,
                'has_visualization': viz_data is not None
            }
            
            # Store visualization data in context for later retrieval
            if viz_data:
                ctx.deps.viz_handler.current_visualization = viz_data
            
            return json.dumps(response)

    async def setup(self, dsn: str, schema: str = 'public'):
        """Setup database connection with specific schema."""
        self.pool = await asyncpg.create_pool(dsn)
        self.schema = schema

        # Set search path for the pool
        async with self.pool.acquire() as conn:
            await conn.execute(f'SET search_path TO {self.schema};')
        
    async def close(self):
        """Close database connection."""
        await self.pool.close()
        
    async def query(self, prompt: str, database: str, schema: str, message_history: str) -> DatabaseResult:
        """Execute a query based on natural language prompt."""
        deps = DatabaseConnection(self.pool, self.viz_handler, database, schema)
        return await self.agent.run(prompt, deps=deps, message_history=message_history)
        
    """ async def query_stream(self, prompt: str):
        
        deps = DatabaseConnection(self.pool, self.viz_handler)
        async with self.agent.run_stream(prompt, deps=deps) as result:
            async for text in result.stream():
                yield text """

async def main():
    # Example usage
    db_agent = DbAgent(viz_dir="./visualizations")
    await db_agent.setup('postgresql://postgres:postgres@localhost:54320/employees')
    
    try:
        """ # Example with streaming
        print("Streaming response:")
        print("Analyzing your question...")
        async for response in db_agent.query_stream("hangi departmanda kaç çalışan var?"):
            print(response, end='', flush=True)
            
        print("\n\nNon-streaming response:")  """
        result = await db_agent.query("departmanları listele")
        debug(result)
        print(f"\nQuery: {result.data.query}")
        print(f"Results: {result.data.results}")
        print(f"Explanation: {result.data.message}")

            
        if result.data.has_visualization:
            # Display visualization directly from binary data
            import matplotlib.pyplot as plt
            import io
            viz_data = db_agent.viz_handler.current_visualization
            img_data = io.BytesIO(viz_data)
            img = plt.imread(img_data, format='png')
            plt.imshow(img)
            plt.axis('off')
            plt.show()
            
    finally:
        await db_agent.close()

if __name__ == "__main__":
    asyncio.run(main())