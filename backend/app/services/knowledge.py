from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import KnowledgeDocument, KnowledgeCategory
from app.schemas.schemas import KnowledgeDocumentCreate, KnowledgeDocumentUpdate, KnowledgeSearchRequest, LanguageCode
from app.database.session import get_db
from fastapi import Depends
from typing import List, Optional
import uuid


class KnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(self, document: KnowledgeDocumentCreate) -> KnowledgeDocument:
        doc_data = document.model_dump()
        if doc_data.get("source_url") is not None:
            doc_data["source_url"] = str(doc_data["source_url"])
        db_doc = KnowledgeDocument(
            id=str(uuid.uuid4()),
            **doc_data,
        )
        self.db.add(db_doc)
        await self.db.commit()
        await self.db.refresh(db_doc)
        return db_doc

    async def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        result = await self.db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        return result.scalar_one_or_none()

    async def update_document(self, doc_id: str, update: KnowledgeDocumentUpdate) -> Optional[KnowledgeDocument]:
        doc = await self.get_document(doc_id)
        if not doc:
            return None

        update_data = update.model_dump(exclude_unset=True)
        if update_data.get("source_url") is not None:
            update_data["source_url"] = str(update_data["source_url"])
        for key, value in update_data.items():
            setattr(doc, key, value)

        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def delete_document(self, doc_id: str) -> bool:
        doc = await self.get_document(doc_id)
        if not doc:
            return False

        await self.db.delete(doc)
        await self.db.commit()
        return True

    async def search_documents(self, request: KnowledgeSearchRequest) -> List[KnowledgeDocument]:
        query = select(KnowledgeDocument)

        if request.category:
            query = query.where(KnowledgeDocument.category == request.category)

        if request.language:
            query = query.where(KnowledgeDocument.language == request.language)

        search_terms = request.query.lower().split()
        if search_terms:
            conditions = []
            for term in search_terms:
                conditions.append(KnowledgeDocument.title.ilike(f"%{term}%"))
                conditions.append(KnowledgeDocument.content.ilike(f"%{term}%"))
            query = query.where(or_(*conditions))

        query = query.order_by(KnowledgeDocument.verified_at.desc().nullslast()).limit(request.limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_documents(self, request: KnowledgeSearchRequest) -> int:
        query = select(func.count(KnowledgeDocument.id))

        if request.category:
            query = query.where(KnowledgeDocument.category == request.category)

        if request.language:
            query = query.where(KnowledgeDocument.language == request.language)

        search_terms = request.query.lower().split()
        if search_terms:
            conditions = []
            for term in search_terms:
                conditions.append(KnowledgeDocument.title.ilike(f"%{term}%"))
                conditions.append(KnowledgeDocument.content.ilike(f"%{term}%"))
            query = query.where(or_(*conditions))

        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_categories(self) -> List[KnowledgeCategory]:
        return list(KnowledgeCategory)

    async def seed_initial_data(self) -> None:
        existing = await self.db.execute(select(func.count(KnowledgeDocument.id)))
        if existing.scalar() > 0:
            return

        sample_docs = [
            KnowledgeDocumentCreate(
                title="PM-KISAN Scheme Overview",
                category=KnowledgeCategory.GOVERNMENT_SCHEMES,
                source_url="https://pmkisan.gov.in/",
                content=(
                    "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi) is a central government scheme that provides "
                    "income support of ₹6,000 per year to all landholding farmer families across India. The amount "
                    "is paid in three equal installments of ₹2,000 each every four months. Eligibility includes "
                    "all farmer families who own cultivable land. Registration can be done online at pmkisan.gov.in "
                    "or through Common Service Centers (CSCs). Required documents include Aadhaar card, bank account "
                    "details, and land ownership documents."
                ),
                language=LanguageCode.EN_IN,
            ),
            KnowledgeDocumentCreate(
                title="पीएम-किसान योजना अवलोकन",
                category=KnowledgeCategory.GOVERNMENT_SCHEMES,
                source_url="https://pmkisan.gov.in/",
                content=(
                    "पीएम-किसान (प्रधान मंत्री किसान सम्मान निधि) एक केंद्रीय सरकारी योजना है जो भारत भर के "
                    "सभी भूमिधारक किसान परिवारों को प्रति वर्ष ₹6,000 की आय सहायता प्रदान करती है। राशि का "
                    "भुगतान हर चार महीने में ₹2,000 की तीन समान किस्तों में किया जाता है। पात्रता में सभी "
                    "किसान परिवार शामिल हैं जिनके पास कृषि योग्य भूमि है। पंजीकरण pmkisan.gov.in पर ऑनलाइन "
                    "या सामान्य सेवा केंद्रों (CSCs) के माध्यम से किया जा सकता है। आवश्यक दस्तावेजों में "
                    "आधार कार्ड, बैंक खाता विवरण और भूमि स्वामित्व दस्तावेज शामिल हैं।"
                ),
                language=LanguageCode.HI_IN,
            ),
            KnowledgeDocumentCreate(
                title="Wheat Cultivation Best Practices",
                category=KnowledgeCategory.AGRICULTURE,
                source_url="https://www.icar.org.in/",
                content=(
                    "Wheat is a major rabi crop in India. Best practices include: sowing between November 15-25 "
                    "for optimal yield; using certified seeds of recommended varieties like HD-2967, HD-3086, DBW-187; "
                    "seed rate of 100-125 kg/ha; row spacing of 20-22.5 cm; applying nitrogen in split doses "
                    "(50% at sowing, 25% at first irrigation, 25% at second irrigation); irrigation at critical stages "
                    "(crown root initiation, tillering, jointing, flowering, grain filling); and weed management "
                    "with pre-emergence herbicides."
                ),
                language=LanguageCode.EN_IN,
            ),
            KnowledgeDocumentCreate(
                title="गेहूं की खेती की सर्वोत्तम प्रथाएं",
                category=KnowledgeCategory.AGRICULTURE,
                source_url="https://www.icar.org.in/",
                content=(
                    "गेहूं भारत में एक प्रमुख रबी फसल है। सर्वोत्तम प्रथाओं में शामिल हैं: इष्टतम उपज के लिए "
                    "15-25 नवंबर के बीच बुवाई; HD-2967, HD-3086, DBW-187 जैसी अनुशंसित किस्मों के प्रमाणित बीजों "
                    "का उपयोग; 100-125 किग्रा/हेक्टेयर बीज दर; 20-22.5 सेमी पंक्ति दूरी; विभाजित खुराकों में "
                    "नाइट्रोजन का प्रयोग (50% बुवाई पर, 25% पहली सिंचाई पर, 25% दूसरी सिंचाई पर); महत्वपूर्ण "
                    "चरणों पर सिंचाई (क्राउन रूट आरंभ, टिलरिंग, जॉइंटिंग, फ्लावरिंग, ग्रेन फिलिंग); और खरपतवार "
                    "प्रबंधन पूर्व-उद्भव हर्बिसाइड्स के साथ।"
                ),
                language=LanguageCode.HI_IN,
            ),
            KnowledgeDocumentCreate(
                title="Finding Nearby Hospitals",
                category=KnowledgeCategory.HOSPITAL_ASSISTANCE,
                source_url="https://www.nhp.gov.in/",
                content=(
                    "To find nearby hospitals in India, you can use the National Health Portal (nhp.gov.in) which "
                    "provides a hospital directory search by state, district, and specialty. Alternatively, use "
                    "Google Maps with search terms like 'government hospital near me' or 'private hospital near me'. "
                    "For emergencies, dial 108 for ambulance services. Many states also have their own health "
                    "department websites with hospital directories. Ayushman Bharat empaneled hospitals can be "
                    "found at pmjay.gov.in."
                ),
                language=LanguageCode.EN_IN,
            ),
            KnowledgeDocumentCreate(
                title="आसपास के अस्पताल ढूंढना",
                category=KnowledgeCategory.HOSPITAL_ASSISTANCE,
                source_url="https://www.nhp.gov.in/",
                content=(
                    "भारत में आसपास के अस्पताल ढूंढने के लिए, आप राष्ट्रीय स्वास्थ्य पोर्टल (nhp.gov.in) का "
                    "उपयोग कर सकते हैं जो राज्य, जिला और विशेषज्ञता के अनुसार अस्पताल निर्देशिका खोज प्रदान "
                    "करता है। वैकल्पिक रूप से, 'मेरे पास सरकारी अस्पताल' या 'मेरे पास निजी अस्पताल' जैसे खोज "
                    "शब्दों के साथ Google Maps का उपयोग करें। आपात स्थिति के लिए, एम्बुलेंस सेवाओं के लिए "
                    "108 डायल करें। कई राज्यों के अपने स्वास्थ्य विभाग की वेबसाइटें भी हैं जिनमें अस्पताल "
                    "निर्देशिकाएं हैं। आयुष्मान भारत सूचीबद्ध अस्पताल pmjay.gov.in पर पाए जा सकते हैं।"
                ),
                language=LanguageCode.HI_IN,
            ),
        ]

        for doc_data in sample_docs:
            await self.create_document(doc_data)


async def get_knowledge_service(db: AsyncSession = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(db)