"""Example data for a fresh install.

    python -m app.seed          insert if the database is empty
    python -m app.seed --force  wipe first, then insert
"""

import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .database import SessionLocal, init_db
from .models import Actor, Case, CaseActor, CaseContact, Contact, Interaction
from .normalize import normalize_identifier

now = datetime.now(timezone.utc)


def contact(**kw):
    kw["normalized"] = normalize_identifier(kw["value"])
    return Contact(**kw)


def days_ago(d, h=0):
    return now - timedelta(days=d, hours=h)


def seed(force=False):
    init_db()
    db = SessionLocal()
    try:
        if force:
            for model in (Interaction, CaseContact, CaseActor, Contact, Case, Actor):
                db.query(model).delete()
            db.commit()

        if db.scalar(select(Case).limit(1)):
            print("Database already has data; use --force to reseed.")
            return

        lockbit = Actor(
            name="LockBitSupp",
            actor_type="ransomware",
            aliases=["LockBit", "putin_gay"],
            description="Public persona of the LockBit RaaS operation.",
            tlp="AMBER",
            first_seen=days_ago(400),
            last_seen=days_ago(3),
        )
        lockbit.contacts = [
            contact(channel_type="tox", value="ABAC...TOXID...9F2E", label="Support Tox"),
            contact(channel_type="url", value="http://lockbitapt.uz/contact", label="Onion mirror"),
        ]

        broker = Actor(
            name="n3tw0rm_broker",
            actor_type="initial_access_broker",
            aliases=["netw0rm", "n3t"],
            description="Sells RDP/VPN access to mid-market targets on XSS.",
            tlp="GREEN",
            first_seen=days_ago(120),
            last_seen=days_ago(1),
        )
        broker.contacts = [
            contact(channel_type="telegram", value="https://t.me/n3tw0rm_deals", label="Deals channel"),
            contact(channel_type="xmpp", value="n3tw0rm@xmpp.jp", label="Negotiation JID"),
            contact(channel_type="forum", value="https://xss.is/members/88213/", label="XSS profile"),
        ]

        shadow = Actor(
            name="ShadowVault",
            actor_type="group",
            aliases=["SV-Team"],
            description="Data-leak extortion crew, active on Telegram.",
            tlp="AMBER",
            first_seen=days_ago(60),
            last_seen=days_ago(6),
        )
        shadow.contacts = [
            contact(channel_type="telegram", value="@ShadowVaultSupport", label="Support bot"),
            contact(channel_type="session", value="05a1b2c3...SESSIONID", label="Session ID"),
        ]

        stealer = Actor(
            name="LogHub",
            actor_type="vendor",
            aliases=["log_hub", "LH_market"],
            description="Stealer-log marketplace operator.",
            tlp="GREEN",
            first_seen=days_ago(210),
            last_seen=days_ago(2),
        )
        stealer.contacts = [
            contact(channel_type="telegram", value="https://t.me/loghub_support", label="Support"),
            contact(channel_type="email", value="loghub@onionmail.org", label="Order mail"),
        ]

        db.add_all([lockbit, broker, shadow, stealer])
        db.flush()

        c1 = Case(
            case_id="OPENCTI-2026-0042",
            title="LockBit affiliate outreach - manufacturing victim",
            source_platform="OpenCTI",
            source_url="https://opencti.local/dashboard/cases/incidents/uuid-0042",
            status="awaiting_response",
            priority="high",
            analyst="g.guler",
            objective="Confirm whether the leaked data is genuine; get a sample file list.",
            tags=["ransomware", "lockbit", "engagement"],
        )
        c1.actor_links = [CaseActor(actor_id=lockbit.id, note="Primary subject")]
        c1.contact_links = [
            CaseContact(contact_id=lockbit.contacts[0].id, outreach_handle="researcher_87")
        ]

        c2 = Case(
            case_id="THEHIVE-1337",
            title="IAB monitoring - n3tw0rm access listing",
            source_platform="TheHive",
            source_url="https://thehive.local/cases/~1337",
            status="responded",
            priority="medium",
            analyst="a.kaya",
            objective="Identify the organisation behind the sanitised access listing.",
            tags=["iab", "xss", "access-broker"],
        )
        c2.actor_links = [CaseActor(actor_id=broker.id)]
        c2.contact_links = [
            CaseContact(contact_id=broker.contacts[1].id, outreach_handle="buyer_de_44"),
        ]

        c3 = Case(
            case_id="SPLUNK-ES-90871",
            title="Extortion claim validation - ShadowVault",
            source_platform="Splunk ES",
            status="open",
            priority="critical",
            analyst="g.guler",
            objective="Validate the breach claim against our telemetry before legal is notified.",
            tags=["extortion", "telegram"],
        )
        c3.actor_links = [CaseActor(actor_id=shadow.id)]
        c3.contact_links = [CaseContact(contact_id=shadow.contacts[0].id)]

        c4 = Case(
            case_id="MISP-2026-5521",
            title="Stealer logs - credentials for our SSO domain",
            source_platform="MISP",
            source_url="https://misp.local/events/view/5521",
            status="tracking",
            priority="high",
            analyst="d.yildiz",
            objective="Buy the relevant log set, scope affected employees.",
            tags=["stealer", "credentials", "loghub"],
        )
        c4.actor_links = [CaseActor(actor_id=stealer.id)]
        c4.contact_links = [
            CaseContact(contact_id=stealer.contacts[0].id, outreach_handle="corp_buyer_1")
        ]

        c5 = Case(
            case_id="INTEL471-IR-7788",
            title="Ransomware negotiation shadowing - retail client",
            source_platform="Intel 471",
            status="awaiting_response",
            priority="critical",
            analyst="a.kaya",
            tags=["ransomware", "negotiation"],
        )
        c5.actor_links = [CaseActor(actor_id=lockbit.id)]

        db.add_all([c1, c2, c3, c4, c5])
        db.flush()

        db.add_all(
            [
                Interaction(
                    case_id=c1.id, contact_id=lockbit.contacts[0].id, direction="outbound",
                    occurred_at=days_ago(4, 2), analyst="g.guler",
                    summary="Opened contact via Tox, asked for proof-of-data.",
                ),
                Interaction(
                    case_id=c1.id, contact_id=lockbit.contacts[0].id, direction="inbound",
                    occurred_at=days_ago(3, 20), analyst="g.guler",
                    summary="Reply: 'proof costs 0.05 BTC, serious buyers only'.",
                ),
                Interaction(
                    case_id=c2.id, contact_id=broker.contacts[1].id, direction="outbound",
                    occurred_at=days_ago(2, 5), analyst="a.kaya",
                    summary="Asked the broker to clarify the target's sector and revenue.",
                ),
                Interaction(
                    case_id=c2.id, contact_id=broker.contacts[1].id, direction="inbound",
                    occurred_at=days_ago(1, 9), analyst="a.kaya",
                    summary="Broker: 'EU, manufacturing, ~$400M, domain admin included'.",
                ),
                Interaction(
                    case_id=c4.id, contact_id=stealer.contacts[0].id, direction="outbound",
                    occurred_at=days_ago(1, 3), analyst="d.yildiz",
                    summary="Requested a preview of logs matching our SSO domain.",
                ),
                Interaction(
                    case_id=c3.id, contact_id=shadow.contacts[0].id, direction="outbound",
                    occurred_at=days_ago(0, 6), analyst="g.guler",
                    summary="Introduced as a researcher, asked what data they claim to hold.",
                ),
            ]
        )
        db.flush()

        # last_seen normally gets set when an interaction is logged through the API
        for inter in db.query(Interaction).all():
            if inter.contact_id:
                c = db.get(Contact, inter.contact_id)
                if c and (c.last_seen is None or c.last_seen < inter.occurred_at):
                    c.last_seen = inter.occurred_at
                    if c.actor:
                        c.actor.last_seen = inter.occurred_at

        db.commit()
        print("Seeded 4 actors, 9 contacts, 5 cases, 6 interactions.")
    finally:
        db.close()


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
