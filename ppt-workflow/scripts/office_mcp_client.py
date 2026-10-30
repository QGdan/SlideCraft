"""Real stdio MCP client. Local validation does not imply Codex has registered this server."""
import asyncio
import argparse
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8",errors="replace")


def parse_request():
    operations={"health":"health_check","catalog":"catalog_native_features","enhance":"apply_editorial_design","instantiate":"create_from_template","unified-template":"create_unified_template","inspect-template":"inspect_template_resources","wps-health":"probe_wps_connection","wps-template":"create_wps_template_copy"}
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=operations)
    parser.add_argument('output',type=Path)
    parser.add_argument('input',type=Path,nargs='?')
    options=parser.parse_args()
    out=options.output.resolve()
    if not out.is_relative_to(ROOT) or out==ROOT:parser.error('Output must be a fresh subdirectory of ppt-workflow')
    if out.exists():parser.error('Output already exists; existing evidence will not be overwritten')
    needs_input=options.operation in ('enhance','instantiate','inspect-template','wps-template')
    if needs_input != (options.input is not None):parser.error('enhance/instantiate/inspect-template/wps-template require exactly one input; other operations accept no input')
    tool=operations[options.operation]
    args={} if options.operation=='health' else {"output_dir":str(out)}
    if options.input:
        value=options.input.resolve()
        if not value.is_relative_to(ROOT) or not value.exists():parser.error('Existing project-local input required')
        key='request_path' if options.operation=='wps-template' else 'sample_dir' if options.operation=='enhance' else 'template_path'
        args[key]=str(value)
    return out,tool,args


async def main(out,tool,args):
    from mcp import Client,StdioServerParameters
    params=StdioServerParameters(command=str(ROOT/".mcp-venv/Scripts/python.exe"),args=[str(ROOT/"office-mcp/server.py")],env={**os.environ,"PYTHONUTF8":"1"},cwd=str(ROOT))
    async with Client(params,read_timeout_seconds=75) as client:
        listing=await client.list_tools()
        if tool not in {t.name for t in listing.tools}:raise RuntimeError('Server does not expose requested tool: '+tool)
        result=await client.call_tool(tool,args,read_timeout_seconds=75)
        record=dict(protocol="MCP stdio",server="ppt-workflow-office",tools=[t.name for t in listing.tools],
                    tool_schemas=[t.model_dump(mode='json') for t in listing.tools],called=tool,arguments=args,result=result.model_dump(mode="json"))
        output=out;output.mkdir(parents=True,exist_ok=True)
        (output/"mcp-client.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(dict(tool=tool,is_error=result.is_error,tools=record["tools"]),ensure_ascii=False))
        failed=result.is_error
    return 1 if failed else 0


if __name__=='__main__':
    request=parse_request()
    raise SystemExit(asyncio.run(main(*request)))
