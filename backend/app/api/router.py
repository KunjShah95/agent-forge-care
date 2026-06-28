from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


def register_routes():
    """Import and include all v1 route modules."""
    from app.api.v1 import (
        auth,
        profile,
        opportunities,
        applications,
        contacts,
        agents,
        memory,
        analytics,
        monitor,
        chat,
        resume,
        notifications,
        status,
        hiring_agent,
    )

    router.include_router(auth.router, prefix="/auth", tags=["Auth"])
    router.include_router(profile.router, prefix="/profile", tags=["Profile"])
    router.include_router(
        opportunities.router, prefix="/opportunities", tags=["Opportunities"]
    )
    router.include_router(
        applications.router, prefix="/applications", tags=["Applications"]
    )
    router.include_router(contacts.router, prefix="/contacts", tags=["Contacts"])
    router.include_router(agents.router, prefix="/agents", tags=["Agents"])
    router.include_router(memory.router, prefix="/memory", tags=["Memory"])
    router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
    router.include_router(monitor.router, prefix="/monitor", tags=["Monitor"])
    router.include_router(chat.router, prefix="/chat", tags=["Chat"])
    router.include_router(resume.router, prefix="/resume", tags=["Resume"])
    router.include_router(
        notifications.router, prefix="/notifications", tags=["Notifications"]
    )
    router.include_router(status.router, tags=["Status"])
    router.include_router(
        hiring_agent.router, prefix="/hiring-agent", tags=["Hiring Agent"]
    )


register_routes()
