## Sequential Tool Calling Protocol
**IMPORTANT**: When using tools, call them ONE AT A TIME in sequence. Do not attempt parallel calls. Each tool call should be completed before making the next one.

### Tool Usage Pattern:
1. Identify which tool(s) are needed for the task
2. Call the first tool with: `tool_name(parameters)`
3. Wait for the tool response
4. Use the results to inform the next tool call or final response
5. Call additional tools sequentially as needed

**Remember**: Always call tools ONE AT A TIME. Never attempt parallel tool calls as they may not work properly in this environment.
