def get_tasks_info_from_globals():
    """Test version - always has the if check."""
    result = []
    for task_id, task_data in scheduled_tasks.items():
        job = scheduler.get_job(task_id)
        if job:
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            next_run = 'Pausada'
        result.append({'id': task_id, **task_data, 'next_run': next_run})
    return result

print("TEST FUNCTION LOADED - if job check present")
