import logging
from typing import List
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings
from jinja2 import Template

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # 自动根据端口调整 SSL/TLS 设置
        use_ssl = settings.MAIL_SSL_TLS
        use_tls = settings.MAIL_STARTTLS
        
        if settings.MAIL_PORT == 465:
            use_ssl = True
            use_tls = False
            logger.info("Detected port 465, forcing SSL=True, STARTTLS=False")
            
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
            MAIL_STARTTLS=use_tls,
            MAIL_SSL_TLS=use_ssl,
            USE_CREDENTIALS=settings.USE_CREDENTIALS,
            VALIDATE_CERTS=settings.VALIDATE_CERTS
        )
        self.fastmail = FastMail(self.conf)

    async def send_doc_update_email(self, to_emails: List[str], doc_title: str, author_name: str, doc_url: str):
        """
        发送文档更新通知邮件
        """
        if not to_emails:
            return

        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
                .container { max-width: 600px; margin: 20px auto; padding: 0; border: 1px solid #e1e4e8; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
                .header { background-color: #24292e; padding: 20px; text-align: center; }
                .header h2 { color: #ffffff; margin: 0; font-size: 20px; font-weight: 600; }
                .content { padding: 30px 25px; background-color: #ffffff; }
                .doc-card { background-color: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6px; padding: 15px; margin: 20px 0; }
                .doc-title { font-size: 18px; font-weight: 600; color: #0366d6; margin: 0 0 5px 0; }
                .author-info { font-size: 14px; color: #586069; }
                .button-container { text-align: center; margin-top: 30px; }
                .button { display: inline-block; padding: 12px 24px; background-color: #2ea44f; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; transition: background-color 0.2s; }
                .button:hover { background-color: #2c974b; }
                .footer { background-color: #f6f8fa; padding: 20px; text-align: center; font-size: 12px; color: #6a737d; border-top: 1px solid #e1e4e8; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>YuqueSync 更新通知</h2>
                </div>
                <div class="content">
                    <p>您好，</p>
                    <p>您关注的成员 <strong>{{ author_name }}</strong> 刚刚更新了文档：</p>
                    
                    <div class="doc-card">
                        <h3 class="doc-title">{{ doc_title }}</h3>
                        <div class="author-info">作者：{{ author_name }}</div>
                    </div>

                    <p>您可以点击下方按钮在 YuqueSync 平台中查看详情：</p>
                    
                    <div class="button-container">
                        <a href="{{ doc_url }}" class="button">查看文档详情</a>
                    </div>
                </div>
                <div class="footer">
                    <p>此邮件由 YuqueSyncPlatform 自动发送，请勿回复。</p>
                    <p>&copy; 2025 YuqueSyncPlatform</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(template_str)
        html_content = template.render(
            author_name=author_name,
            doc_title=doc_title,
            doc_url=doc_url
        )

        message = MessageSchema(
            subject=f"【语雀更新】{author_name} 发布了《{doc_title}》",
            recipients=to_emails,
            body=html_content,
            subtype=MessageType.html
        )

        try:
            await self.fastmail.send_message(message)
            logger.info(f"Email sent to {len(to_emails)} recipients for doc: {doc_title}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    async def send_test_email(self, to_email: str):
        """
        发送测试邮件
        """
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 5px; }
                .header { background-color: #f8f9fa; padding: 10px 20px; border-bottom: 1px solid #eee; }
                .content { padding: 20px; }
                .footer { font-size: 12px; color: #999; text-align: center; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>测试邮件</h2>
                </div>
                <div class="content">
                    <p>您好，</p>
                    <p>这是一封来自 YuqueSyncPlatform 的测试邮件。</p>
                    <p>如果您收到这封邮件，说明邮件服务配置正确。</p>
                </div>
                <div class="footer">
                    <p>此邮件由 YuqueSyncPlatform 自动发送，请勿回复。</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject="【测试】YuqueSyncPlatform 邮件服务测试",
            recipients=[to_email],
            body=template_str,
            subtype=MessageType.html
        )

        try:
            await self.fastmail.send_message(message)
            logger.info(f"Test email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send test email: {e}")
            raise e
