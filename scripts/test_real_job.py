import asyncio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.jobs.manager import job_manager, JobStatus
from backend.browser.wuolah import WuolahBrowser

async def test_job():
    target_url = "https://wuolah.com/apuntes/sistemas-operativos-i/preguntas-examen-ssoo-i-pdf-14080870"
    browser = WuolahBrowser(headless=True)
    
    try:
        print("1. Creando job en JobManager...")
        job = await job_manager.create_job(target_url)
        job_id = job["job_id"]
        print(f"   Job ID: {job_id}, Status: {job['status']}")
        
        # Launch run_document_pipeline in background task
        task = asyncio.create_task(
            job_manager.run_document_pipeline(job_id=job_id, url=target_url, browser=browser)
        )
        
        t0 = time.time()
        while not task.done():
            await asyncio.sleep(0.4)
            j = await job_manager.get_job(job_id)
            elapsed = time.time() - t0
            print(f"   [{elapsed:.1f}s] Status: {j['status']} ({j.get('progress')}%), Msg: {j.get('message')}")
            if j["status"] in [JobStatus.READY, JobStatus.ERROR]:
                break
                
        await task
        j = await job_manager.get_job(job_id)
        total_time = time.time() - t0
        print(f"\n--- RESULTADO FINAL en {total_time:.2f}s ---")
        print("Status:", j["status"])
        print("Message:", j["message"])
        print("Filename:", j["filename"])
        print("Result Path:", j["result_path"])
        print("Metadata:", j["result_metadata"])
        
        assert j["status"] == JobStatus.READY, f"El job terminó en estado {j['status']}: {j.get('error')}"
        print("¡TODO EL PIPELINE COMPLETADO EXITOSAMENTE!")
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_job())
