from pathlib import Path

def test_v105_all_stage_documents_exist():
    root=Path(__file__).parents[1]/'docs'
    for i in range(1,19):
        assert (root/f'V105.{i:02d}_CLOSED.md').exists()

def test_v105_release_artifacts_exist():
    root=Path(__file__).parents[1]
    for p in ['Dockerfile.prod','docker-compose.prod.yml','.github/workflows/ci.yml','docs/V105_PRODUCTION_MANIFEST.md']:
        assert (root/p).exists()
