"""
HTML Email Templates for Retention Notifications
Professional, mobile-responsive templates
"""
from typing import List, Dict, Any
from datetime import datetime


class EmailTemplate:
    """Base class for email templates"""
    
    @staticmethod
    def render_plain_text(**kwargs) -> str:
        """Render plain text version"""
        raise NotImplementedError
    
    @staticmethod
    def render_html(**kwargs) -> str:
        """Render HTML version"""
        raise NotImplementedError


class RetentionNotificationTemplate(EmailTemplate):
    """Template for artifact retention expiration notifications"""
    
    @staticmethod
    def render_plain_text(
        plan: str,
        artifacts: List[Dict[str, Any]],
        deletion_groups: Dict[int, List[Dict[str, Any]]]
    ) -> str:
        """
        Render plain text email
        
        Args:
            plan: Subscription plan
            artifacts: List of artifacts
            deletion_groups: Artifacts grouped by days until deletion
        
        Returns:
            Plain text email body
        """
        total_artifacts = len(artifacts)
        
        body_parts = [
            f"Hello,",
            f"",
            f"This is a reminder that {total_artifacts} of your content artifacts will be deleted soon due to your {plan.upper()} plan retention policy.",
            f"",
            f"Artifacts by expiration:"
        ]
        
        for days in sorted(deletion_groups.keys()):
            group_artifacts = deletion_groups[days]
            days_text = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
            body_parts.append(f"")
            body_parts.append(f"Expiring {days_text}: {len(group_artifacts)} artifact{'s' if len(group_artifacts) != 1 else ''}")
            
            # Show first 5 artifacts in each group
            for artifact in group_artifacts[:5]:
                body_parts.append(f"  - {artifact['type']}: {artifact['topic'][:50]}")
            
            if len(group_artifacts) > 5:
                body_parts.append(f"  ... and {len(group_artifacts) - 5} more")
        
        body_parts.extend([
            f"",
            f"What you can do:",
            f"  1. Download your content before it's deleted",
            f"  2. Upgrade your plan for longer retention:",
            f"     - Basic: 90 days",
            f"     - Pro: 365 days",
            f"     - Enterprise: Unlimited",
            f"",
            f"⚠️ Once deleted, your content cannot be recovered.",
            f"",
            f"Questions? Contact support@contentcreationcrew.com",
            f"",
            f"Best regards,",
            f"Content Creation Crew Team"
        ])
        
        return "\n".join(body_parts)
    
    @staticmethod
    def render_html(
        plan: str,
        artifacts: List[Dict[str, Any]],
        deletion_groups: Dict[int, List[Dict[str, Any]]]
    ) -> str:
        """
        Render HTML email with professional styling
        
        Args:
            plan: Subscription plan
            artifacts: List of artifacts
            deletion_groups: Artifacts grouped by days until deletion
        
        Returns:
            HTML email body
        """
        total_artifacts = len(artifacts)
        
        # Build artifact groups HTML
        groups_html = []
        for days in sorted(deletion_groups.keys()):
            group_artifacts = deletion_groups[days]
            days_text = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
            
            # Determine urgency color
            if days == 0:
                urgency_color = "#dc3545"  # Red
                urgency_label = "URGENT"
            elif days <= 3:
                urgency_color = "#fd7e14"  # Orange
                urgency_label = "HIGH PRIORITY"
            else:
                urgency_color = "#ffc107"  # Yellow
                urgency_label = "NOTICE"
            
            artifact_items = []
            for artifact in group_artifacts[:5]:
                artifact_items.append(f"""
                    <tr>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #e9ecef;">
                            <span style="display: inline-block; padding: 2px 8px; background: #e9ecef; border-radius: 4px; font-size: 12px; text-transform: uppercase; color: #495057; margin-right: 8px;">{artifact['type']}</span>
                            <span style="color: #212529;">{artifact['topic'][:60]}</span>
                        </td>
                    </tr>
                """)
            
            if len(group_artifacts) > 5:
                artifact_items.append(f"""
                    <tr>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #e9ecef; color: #6c757d; font-style: italic;">
                            ... and {len(group_artifacts) - 5} more artifact{'s' if len(group_artifacts) - 5 != 1 else ''}
                        </td>
                    </tr>
                """)
            
            groups_html.append(f"""
                <div style="margin-bottom: 24px; border: 2px solid {urgency_color}; border-radius: 8px; overflow: hidden;">
                    <div style="background: {urgency_color}; color: white; padding: 12px 16px; font-weight: 600;">
                        <span style="font-size: 11px; opacity: 0.9;">{urgency_label}</span><br/>
                        Expiring {days_text}: {len(group_artifacts)} artifact{'s' if len(group_artifacts) != 1 else ''}
                    </div>
                    <table style="width: 100%; background: white;">
                        {''.join(artifact_items)}
                    </table>
                </div>
            """)
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Expiration Notice</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8f9fa;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px 40px; text-align: center;">
                            <h1 style="margin: 0; color: white; font-size: 24px; font-weight: 600;">
                                ⚠️ Content Expiration Notice
                            </h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">
                                {total_artifacts} artifact{'s' if total_artifacts != 1 else ''} will be deleted soon
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px;">
                            
                            <!-- Intro -->
                            <p style="margin: 0 0 24px 0; color: #212529; font-size: 16px; line-height: 1.5;">
                                Hello,
                            </p>
                            
                            <p style="margin: 0 0 24px 0; color: #495057; font-size: 15px; line-height: 1.6;">
                                This is a reminder that <strong>{total_artifacts} of your content artifacts</strong> will be automatically deleted soon due to your <strong style="text-transform: uppercase; color: #667eea;">{plan} plan</strong> retention policy.
                            </p>
                            
                            <!-- Artifacts by expiration -->
                            <h2 style="margin: 32px 0 16px 0; color: #212529; font-size: 18px; font-weight: 600;">
                                📅 Your Expiring Content
                            </h2>
                            
                            {''.join(groups_html)}
                            
                            <!-- Action Items -->
                            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; margin: 32px 0; border-radius: 4px;">
                                <h3 style="margin: 0 0 12px 0; color: #856404; font-size: 16px; font-weight: 600;">
                                    🔔 What You Can Do
                                </h3>
                                <ol style="margin: 0; padding-left: 24px; color: #856404;">
                                    <li style="margin-bottom: 8px;">Download your content before it's deleted</li>
                                    <li style="margin-bottom: 8px;">Upgrade your plan for longer retention:
                                        <ul style="margin-top: 8px;">
                                            <li><strong>Basic:</strong> 90 days retention</li>
                                            <li><strong>Pro:</strong> 365 days retention</li>
                                            <li><strong>Enterprise:</strong> Unlimited retention</li>
                                        </ul>
                                    </li>
                                </ol>
                            </div>
                            
                            <!-- Warning -->
                            <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 16px; margin: 24px 0; border-radius: 4px;">
                                <p style="margin: 0; color: #721c24; font-weight: 600; font-size: 14px;">
                                    ⚠️ Once deleted, your content cannot be recovered.
                                </p>
                            </div>
                            
                            <!-- CTA Button -->
                            <div style="text-align: center; margin: 32px 0;">
                                <a href="https://app.contentcreationcrew.com/billing" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 600; font-size: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                    Upgrade Your Plan →
                                </a>
                            </div>
                            
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background: #f8f9fa; padding: 24px 40px; border-top: 1px solid #e9ecef;">
                            <p style="margin: 0 0 8px 0; color: #6c757d; font-size: 13px; text-align: center;">
                                Questions? Contact us at <a href="mailto:support@contentcreationcrew.com" style="color: #667eea; text-decoration: none;">support@contentcreationcrew.com</a>
                            </p>
                            <p style="margin: 0; color: #adb5bd; font-size: 12px; text-align: center;">
                                © {datetime.now().year} Content Creation Crew. All rights reserved.
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        return html.strip()

