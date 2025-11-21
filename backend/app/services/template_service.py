# backend/app/services/template_service.py
"""
Meeting Template Service
Manages pre-defined and custom meeting templates for structured note-taking
"""

from typing import Optional, List, Dict
import logging
from sqlalchemy.orm import Session
import json

from ..models import MeetingTemplate, User
from datetime import datetime

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing meeting templates"""

    # System templates (pre-defined)
    SYSTEM_TEMPLATES = [
        {
            "name": "1-on-1 Meeting",
            "description": "One-on-one conversation template with check-ins and action items",
            "icon": "users",
            "color": "#3B82F6",
            "structure": {
                "sections": [
                    "Check-in & Updates",
                    "Discussion Topics",
                    "Action Items",
                    "Next Meeting"
                ]
            },
            "summary_prompt": """
Summarize this 1-on-1 meeting focusing on:
1. Key updates shared
2. Main discussion points
3. Action items agreed upon
4. Topics for next meeting

Meeting: {title}
Transcript: {transcript}
""",
            "auto_extract_action_items": True,
            "auto_extract_decisions": True
        },
        {
            "name": "Customer Discovery",
            "description": "Customer interview and discovery call template",
            "icon": "search",
            "color": "#10B981",
            "structure": {
                "sections": [
                    "Customer Background",
                    "Pain Points",
                    "Current Solutions",
                    "Feature Requests",
                    "Next Steps"
                ]
            },
            "summary_prompt": """
Summarize this customer discovery call focusing on:
1. Customer profile and background
2. Key pain points identified
3. Current solutions they're using
4. Feature requests and needs
5. Follow-up actions

Meeting: {title}
Transcript: {transcript}
""",
            "auto_extract_action_items": True,
            "auto_extract_decisions": False
        },
        {
            "name": "Team Standup",
            "description": "Daily standup meeting template",
            "icon": "calendar-check",
            "color": "#F59E0B",
            "structure": {
                "sections": [
                    "Yesterday's Progress",
                    "Today's Plan",
                    "Blockers",
                    "Announcements"
                ]
            },
            "summary_prompt": """
Summarize this standup meeting with:
1. What was accomplished yesterday
2. Plans for today
3. Any blockers or impediments
4. Team announcements

Meeting: {title}
Transcript: {transcript}
""",
            "auto_extract_action_items": True,
            "auto_extract_decisions": False
        },
        {
            "name": "Sales Call",
            "description": "Sales and demo call template",
            "icon": "trending-up",
            "color": "#EF4444",
            "structure": {
                "sections": [
                    "Prospect Info",
                    "Current Situation",
                    "Demo Notes",
                    "Objections",
                    "Pricing Discussion",
                    "Next Steps"
                ]
            },
            "summary_prompt": """
Summarize this sales call including:
1. Prospect information and company
2. Their current situation and needs
3. Demo highlights and reactions
4. Objections raised and how addressed
5. Pricing discussion
6. Agreed next steps

Meeting: {title}
Transcript: {transcript}
""",
            "auto_extract_action_items": True,
            "auto_extract_decisions": True
        },
        {
            "name": "User Interview",
            "description": "User research and interview template",
            "icon": "clipboard-list",
            "color": "#8B5CF6",
            "structure": {
                "sections": [
                    "User Background",
                    "Usage Patterns",
                    "Pain Points",
                    "Feature Feedback",
                    "Insights"
                ]
            },
            "summary_prompt": """
Summarize this user interview focusing on:
1. User background and context
2. How they use the product
3. Pain points experienced
4. Feedback on specific features
5. Key insights and learnings

Meeting: {title}
Transcript: {transcript}
""",
            "auto_extract_action_items": False,
            "auto_extract_decisions": False
        },
        {
            "name": "Brainstorming Session",
            "description": "Creative ideation and brainstorming template",
            "icon": "lightbulb",
            "color": "#EC4899",
            "structure": {
                "sections": [
                    "Problem Statement",
                    "Ideas Generated",
                    "Top Picks",
                    "Action Items"
                ]
            },
            "summary_prompt": """
Summarize this brainstorming session with:
1. Problem or challenge being addressed
2. All ideas generated
3. Top ideas selected
4. Next steps to explore ideas

Meeting: {title}
Transcript: {transcript}
""",
            "auto_extract_action_items": True,
            "auto_extract_decisions": True
        },
        {
            "name": "Project Kickoff",
            "description": "Project kickoff meeting template",
            "icon": "rocket",
            "color": "#14B8A6",
            "structure": {
                "sections": [
                    "Project Goals",
                    "Team Roles",
                    "Timeline",
                    "Success Metrics",
                    "Next Steps"
                ]
            },
            "summary_prompt": """
Summarize this project kickoff meeting:
1. Project goals and objectives
2. Team members and roles
3. Timeline and milestones
4. Success metrics
5. Immediate next steps

Meeting: {title}
Transcript: {transcript}
""",
            "auto_extract_action_items": True,
            "auto_extract_decisions": True
        }
    ]

    @staticmethod
    def initialize_system_templates(db: Session):
        """
        Initialize system templates in database
        Called during app startup or first-time setup

        Args:
            db: Database session
        """
        try:
            for template_data in TemplateService.SYSTEM_TEMPLATES:
                # Check if template already exists
                existing = db.query(MeetingTemplate).filter(
                    MeetingTemplate.name == template_data['name'],
                    MeetingTemplate.is_system_template == True
                ).first()

                if not existing:
                    template = MeetingTemplate(
                        user_id=None,  # System template
                        name=template_data['name'],
                        description=template_data['description'],
                        is_system_template=True,
                        is_public=True,
                        structure=json.dumps(template_data['structure']),
                        summary_prompt=template_data['summary_prompt'],
                        auto_extract_action_items=template_data['auto_extract_action_items'],
                        auto_extract_decisions=template_data['auto_extract_decisions'],
                        icon=template_data['icon'],
                        color=template_data['color']
                    )
                    db.add(template)

            db.commit()
            logger.info(f"Initialized {len(TemplateService.SYSTEM_TEMPLATES)} system templates")

        except Exception as e:
            logger.error(f"Error initializing system templates: {e}")
            db.rollback()

    @staticmethod
    def create_custom_template(
        user_id: str,
        name: str,
        description: str,
        db: Session,
        structure: Optional[Dict] = None,
        summary_prompt: Optional[str] = None,
        **kwargs
    ) -> MeetingTemplate:
        """
        Create a custom user template

        Args:
            user_id: User ID
            name: Template name
            description: Template description
            db: Database session
            structure: Template structure dict
            summary_prompt: Custom summary prompt
            **kwargs: Additional fields

        Returns:
            MeetingTemplate object
        """
        try:
            template = MeetingTemplate(
                user_id=user_id,
                name=name,
                description=description,
                is_system_template=False,
                structure=json.dumps(structure) if structure else None,
                summary_prompt=summary_prompt,
                **kwargs
            )

            db.add(template)
            db.commit()
            db.refresh(template)

            logger.info(f"Created custom template '{name}' for user {user_id}")
            return template

        except Exception as e:
            logger.error(f"Error creating custom template: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_templates(
        user_id: Optional[str],
        db: Session,
        include_system: bool = True
    ) -> List[MeetingTemplate]:
        """
        Get templates available to a user

        Args:
            user_id: User ID (None for system templates only)
            db: Database session
            include_system: Include system templates

        Returns:
            List of MeetingTemplate objects
        """
        templates = []

        # Get system templates
        if include_system:
            system_templates = db.query(MeetingTemplate).filter(
                MeetingTemplate.is_system_template == True
            ).all()
            templates.extend(system_templates)

        # Get user's custom templates
        if user_id:
            user_templates = db.query(MeetingTemplate).filter(
                MeetingTemplate.user_id == user_id,
                MeetingTemplate.is_system_template == False
            ).all()
            templates.extend(user_templates)

        return templates

    @staticmethod
    def get_template(template_id: str, db: Session) -> Optional[MeetingTemplate]:
        """Get a specific template by ID"""
        return db.query(MeetingTemplate).get(template_id)

    @staticmethod
    def update_template(
        template_id: str,
        db: Session,
        **updates
    ) -> MeetingTemplate:
        """
        Update a template

        Args:
            template_id: Template ID
            db: Database session
            **updates: Fields to update

        Returns:
            Updated MeetingTemplate
        """
        template = db.query(MeetingTemplate).get(template_id)
        if not template:
            raise ValueError("Template not found")

        if template.is_system_template:
            raise ValueError("Cannot modify system templates")

        for key, value in updates.items():
            if hasattr(template, key):
                if key == 'structure' and isinstance(value, dict):
                    setattr(template, key, json.dumps(value))
                else:
                    setattr(template, key, value)

        template.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(template)

        logger.info(f"Updated template {template_id}")
        return template

    @staticmethod
    def delete_template(template_id: str, db: Session) -> bool:
        """
        Delete a custom template

        Args:
            template_id: Template ID
            db: Database session

        Returns:
            True if successful
        """
        template = db.query(MeetingTemplate).get(template_id)
        if not template:
            return False

        if template.is_system_template:
            raise ValueError("Cannot delete system templates")

        db.delete(template)
        db.commit()

        logger.info(f"Deleted template {template_id}")
        return True

    @staticmethod
    def apply_template_to_meeting(
        template: MeetingTemplate,
        meeting_id: str,
        db: Session
    ) -> bool:
        """
        Apply a template to a meeting

        Args:
            template: MeetingTemplate object
            meeting_id: Meeting ID
            db: Database session

        Returns:
            True if successful
        """
        from ..models import Meeting

        meeting = db.query(Meeting).get(meeting_id)
        if not meeting:
            return False

        meeting.template_id = template.id
        meeting.updated_at = datetime.utcnow()

        # Increment template usage
        template.usage_count += 1

        db.commit()

        logger.info(f"Applied template {template.id} to meeting {meeting_id}")
        return True
