from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from lineage_config import LINEAGE_MAP

router = APIRouter(prefix="/lineage", tags=["Lineage"])

def _success(message, data):
    return {
        "success": True,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data
    }

@router.get("", summary="Get Complete Data Lineage Graph")
def get_complete_lineage():
    nodes = []
    edges = []
    
    added_nodes = set()

    for pipeline, mapping in LINEAGE_MAP.items():
        # Add pipeline node
        if pipeline not in added_nodes:
            nodes.append({
                "id": pipeline,
                "label": pipeline,
                "type": "pipeline"
            })
            added_nodes.add(pipeline)

        # Add source nodes and edges
        for src in mapping["sources"]:
            if src not in added_nodes:
                nodes.append({
                    "id": src,
                    "label": src,
                    "type": "table",
                    "environment": "source"
                })
                added_nodes.add(src)
            edges.append({
                "source": src,
                "target": pipeline
            })

        # Add target nodes and edges
        for tgt in mapping["targets"]:
            if tgt not in added_nodes:
                nodes.append({
                    "id": tgt,
                    "label": tgt,
                    "type": "table",
                    "environment": "target"
                })
                added_nodes.add(tgt)
            edges.append({
                "source": pipeline,
                "target": tgt
            })

    return _success(
        "Data lineage graph generated successfully",
        {"nodes": nodes, "edges": edges}
    )

@router.get("/{pipeline_name}", summary="Get Pipeline Lineage Details")
def get_pipeline_lineage(pipeline_name: str):
    if pipeline_name not in LINEAGE_MAP:
        raise HTTPException(status_code=404, detail="Pipeline lineage details not found")
        
    return _success(
        f"Lineage details retrieved for {pipeline_name}",
        LINEAGE_MAP[pipeline_name]
    )
