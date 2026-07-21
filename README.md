🚀 **Zero-Cost Revenue Engine**
AI-Powered Sales Automation System (Fully Self-Hosted)
🌐 **Live Demo** : [https://zero-cost-revenue-engine.onrender.com/](https://zero-cost-revenue-engine.onrender.com/)

📌 **Overview**
The Zero-Cost Revenue Engine is a full-stack, AI-powered sales automation platform designed to replace expensive SaaS tools like HubSpot, Apollo, and Zapier.
It automates the complete outreach pipeline — from lead discovery to AI-personalized email delivery — while maintaining zero operational cost using a fully self-hosted architecture.

💡 Built for scalability, efficiency, and real-world business impact.

**Key Features**
🔍 **Automated Lead Extraction**
Scrapes websites and extracts relevant business insights
🤖 **AI-Powered Personalization**
Generates context-aware outreach emails using LLM APIs
👨‍💻 **Human-in-the-Loop Approval**
Review and edit AI-generated emails before sending
📧 **Automated Email Dispatch**
Sends emails via SMTP (Gmail / SendGrid / Brevo)
🗂 **Lead Lifecycle Management**
Tracks leads using a structured SQLite database
🔒 **Idempotent System Design**
Prevents duplicate leads and redundant email sending
🏗️ **System Architecture**
[Data Extraction] → [State Database] → [AI Personalizer] → [Human Review] → [Email Dispatcher]

**Tech Stack**
**Layer**	**Technology Used**
Backend:    Python, Flask
Database:	  SQLite
Frontend:	  HTML5, CSS3 (Glassmorphism UI)
AI Engine:  Google Gemini API (Free Tier)
Deployment: Render
Email:	    SMTP (Gmail / SendGrid / Brevo)

📂 **Project Structure**
├── extractor.py        # Web scraping & data extraction
├── db.py               # Database & lead tracking
├── personalizer.py     # AI email generation
├── dispatcher.py       # Email delivery system
├── app.py              # Flask dashboard (main server)
├── templates/          # HTML templates
├── static/             # CSS & frontend assets
├── test_pipeline.py    # Pipeline testing
├── requirements.txt    # Dependencies

🚀 **Getting Started**
1️. Clone the Repository
git clone https://github.com/your-username/zero-cost-revenue-engine.git
cd zero-cost-revenue-engine
2️. Install Dependencies
pip install -r requirements.txt
3️. Run the Application
python app.py
4️. Access the Dashboard
http://localhost:5000/

📊 **Business Impact**
| Feature            | Traditional SaaS Tools | This Project |
| ------------------ | ---------------------- | ------------ |
| Lead Scraping      | Paid                   | Free         |
| Email Automation   | Paid                   | Free         |
| AI Personalization | Paid                   | Free         |
| Integration        | Paid                   | Free         |
| **Total Cost**     | **$800–$1100/month**   | **$0/month** |

🚀 Enables startups and developers to build scalable outreach systems without recurring costs.

🧠 **Design Principles**
**Cost Efficiency** → Eliminates SaaS dependency
**Scalability** → Supports large lead volumes
**Reliability** → Fallback mechanisms for AI/API failures
**Modularity** → Easy to extend and customize
**Control** → Human approval ensures quality outreach

🧑‍💻 Author
**Sweta Pramanick**
B.Tech CSE | AI & Full Stack Developer

📌 **Future Improvements**
Multi-user authentication system
Advanced analytics dashboard
CRM integration
Bulk campaign scheduling

⭐ **Support**
If you found this project useful, consider giving it a ⭐ on GitHub!

📜 **License**
This project is open-source and available under the MIT License.
