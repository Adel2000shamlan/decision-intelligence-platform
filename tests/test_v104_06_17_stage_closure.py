from app.core.implementation_registry import ImplementationRegistry

def test_requested_stage_registry_is_closed():
 r=ImplementationRegistry()
 stages=['V104.06.01','V104.06.02','V104.06.03','V104.06.04','V104.06.05','V104.06.06','V104.06.07','V104.06.08','V104.06.09','V104.06.10','V104.06.11','V104.06.12','V104.06.13','V104.06.14','V104.06.15','V104.06.16','V104.06.17','V104.07','V104.08','V104.09','V104.10','V104.11','V104.12','V104.13','V104.14','V104.15','V104.16','V104.17']
 for x in stages:r.add(x,x)
 assert len(r.stages)==28 and r.assert_closed()
