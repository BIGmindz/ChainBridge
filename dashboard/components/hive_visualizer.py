"""
ChainBridge Hive Visualizer Component
PAC-VIZ-P55: 3-of-5 Voting Grid Visualization

Renders individual atom voting states in polyatomic consensus:
- AGREE (Green): Atom voted for majority hash
- DISAGREE (Red): Atom voted for minority hash
- PENDING (Gray): Atom has not voted yet
- TIMEOUT (Yellow): Atom failed to respond

Invariant: VIZ-01 (Truth in UI) - Visual state matches actual atom vote
"""

import streamlit as st
from typing import List
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.orchestration.metrics_stream import (
    ConsensusEvent,
    AtomVote,
    AtomVoteState
)


def render_atom_card(vote: AtomVote, index: int):
    """
    Render individual atom voting card.
    
    Args:
        vote: AtomVote object with state
        index: Atom index in squad (0-4 for 5-atom squad)
    
    Displays:
        - GID
        - Vote state icon
        - Hash snippet
        - Latency
    """
    # Determine colors based on vote state
    state_config = {
        AtomVoteState.AGREE: {
            "color": "#00ff00",
            "icon": "✅",
            "text_color": "#000",
            "label": "AGREE"
        },
        AtomVoteState.DISAGREE: {
            "color": "#ff0000",
            "icon": "❌",
            "text_color": "#fff",
            "label": "DISAGREE"
        },
        AtomVoteState.PENDING: {
            "color": "#888888",
            "icon": "⏳",
            "text_color": "#fff",
            "label": "PENDING"
        },
        AtomVoteState.TIMEOUT: {
            "color": "#ffaa00",
            "icon": "⚠️",
            "text_color": "#000",
            "label": "TIMEOUT"
        },
        AtomVoteState.SYNCING: {
            "color": "#00aaff",
            "icon": "🔄",
            "text_color": "#fff",
            "label": "SYNCING"
        }
    }
    
    config = state_config.get(vote.vote_state, state_config[AtomVoteState.PENDING])
    
    # Render card using HTML/CSS
    st.markdown(
        f"""
        <div style="
            background-color: {config['color']};
            color: {config['text_color']};
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        ">
            <div style="font-size: 2em;">{config['icon']}</div>
            <div style="font-weight: bold; font-size: 1.1em;">{vote.gid}</div>
            <div style="font-size: 0.9em; opacity: 0.8;">{config['label']}</div>
            <div style="font-size: 0.8em; font-family: monospace; margin-top: 5px;">
                {vote.hash[:8]}...
            </div>
            <div style="font-size: 0.75em; margin-top: 3px;">
                {vote.latency_ms:.1f}ms
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_voting_grid(event: ConsensusEvent):
    """
    Render complete voting grid for consensus event.
    
    Args:
        event: ConsensusEvent with atom votes
    
    Displays:
        - Grid of atom cards (1 row x N columns)
        - Consensus result summary
        - Vote distribution
    """
    st.subheader(f"Consensus: {event.consensus_id}")
    
    # Event metadata
    st.text(f"Task: {event.task_description}")
    st.text(f"Context Hash: {event.context_hash[:32]}...")
    st.text(f"Timestamp: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Voting grid
    st.markdown("### Atom Votes")
    
    # Create columns for each atom
    cols = st.columns(len(event.atom_votes))
    
    for i, vote in enumerate(event.atom_votes):
        with cols[i]:
            render_atom_card(vote, i)
    
    # Consensus result
    st.divider()
    
    result_col1, result_col2 = st.columns(2)
    
    with result_col1:
        st.markdown("### Consensus Result")
        
        if event.achieved:
            st.success(f"✅ **CONSENSUS ACHIEVED**")
            st.text(f"Threshold: {event.threshold}/{len(event.atom_votes)}")
            st.text(f"Winning Hash: {event.winning_hash[:16]}...")
        else:
            st.error(f"❌ **DISSONANCE DETECTED**")
            st.text(f"Failed to reach {event.threshold}/{len(event.atom_votes)} threshold")
            st.text("POLY-02 TRIGGERED: Fail-Closed")
    
    with result_col2:
        st.markdown("### Vote Distribution")
        
        # Build vote table
        vote_table = []
        for hash_val, count in event.vote_count.items():
            vote_table.append({
                "Hash": hash_val[:16] + "...",
                "Votes": count,
                "Percentage": f"{count / len(event.atom_votes) * 100:.1f}%"
            })
        
        if vote_table:
            import pandas as pd
            df = pd.DataFrame(vote_table)
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.text("No votes recorded")


def render_consensus_summary(event: ConsensusEvent):
    """
    Render compact consensus summary (for history view).
    
    Args:
        event: ConsensusEvent to summarize
    
    Displays:
        - Consensus ID
        - Result (✅/❌)
        - Vote ratio
        - Timestamp
    """
    status_icon = "✅" if event.achieved else "❌"
    status_text = "CONSENSUS" if event.achieved else "DISSONANCE"
    
    # Vote ratio
    max_votes = max(event.vote_count.values()) if event.vote_count else 0
    vote_ratio = f"{max_votes}/{len(event.atom_votes)}"
    
    # Average latency
    avg_latency = sum(v.latency_ms for v in event.atom_votes) / len(event.atom_votes)
    
    st.markdown(
        f"""
        <div style="
            border-left: 4px solid {'#00ff00' if event.achieved else '#ff0000'};
            padding: 10px;
            margin: 5px 0;
            background-color: rgba(255,255,255,0.05);
        ">
            <div style="font-weight: bold;">{status_icon} {event.consensus_id} - {status_text}</div>
            <div style="font-size: 0.9em; opacity: 0.8;">
                Task: {event.task_description[:50]}{'...' if len(event.task_description) > 50 else ''}
            </div>
            <div style="font-size: 0.85em; margin-top: 5px;">
                Votes: {vote_ratio} | Latency: {avg_latency:.1f}ms | {event.timestamp.strftime('%H:%M:%S')}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_live_feed(events: List[ConsensusEvent], max_events: int = 10):
    """
    Render live consensus event feed.
    
    Args:
        events: List of ConsensusEvent (newest first)
        max_events: Maximum events to display
    
    Displays:
        - Scrollable feed of recent consensus events
        - Compact summaries
    """
    st.markdown("### Live Consensus Feed")
    
    if not events:
        st.info("No consensus events yet. Waiting for first vote...")
        return
    
    # Limit to max_events
    display_events = events[:max_events]
    
    for event in display_events:
        render_consensus_summary(event)


def render_health_indicator(health_state):
    """
    Render system health indicator.
    
    Args:
        health_state: HiveHealthState enum
    
    Displays:
        - Health status with color coding
        - Blinking red if SCRAM
    """
    from core.orchestration.metrics_stream import HiveHealthState
    
    health_config = {
        HiveHealthState.OPERATIONAL: {
            "color": "#00ff00",
            "icon": "✅",
            "text": "OPERATIONAL",
            "blink": False
        },
        HiveHealthState.DEGRADED: {
            "color": "#ffaa00",
            "icon": "⚠️",
            "text": "DEGRADED",
            "blink": False
        },
        HiveHealthState.SCRAM: {
            "color": "#ff0000",
            "icon": "🚨",
            "text": "SCRAM",
            "blink": True
        },
        HiveHealthState.RECOVERING: {
            "color": "#00aaff",
            "icon": "🔄",
            "text": "RECOVERING",
            "blink": False
        }
    }
    
    config = health_config.get(health_state, health_config[HiveHealthState.OPERATIONAL])
    
    # Add blinking animation for SCRAM
    animation = """
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
    }
    """ if config["blink"] else ""
    
    st.markdown(
        f"""
        <style>{animation}</style>
        <div style="
            background-color: {config['color']};
            color: #000;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 1.5em;
            font-weight: bold;
            animation: {'blink 1s infinite' if config['blink'] else 'none'};
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        ">
            {config['icon']} SYSTEM STATUS: {config['text']}
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================================
# DEMO / TESTING
# ============================================================================

if __name__ == "__main__":
    st.set_page_config(page_title="Hive Visualizer Demo", layout="wide")
    st.title("Hive Visualizer Component Demo")
    
    # Import metrics stream
    from core.orchestration.metrics_stream import get_latest_consensus_events, get_hive_health
    
    # Get sample data
    events = get_latest_consensus_events(count=5)
    health = get_hive_health()
    
    # Demo: Health Indicator
    st.header("Health Indicator")
    render_health_indicator(health)
    
    st.divider()
    
    # Demo: Voting Grid
    if events:
        st.header("Voting Grid (Latest Event)")
        render_voting_grid(events[0])
        
        st.divider()
        
        # Demo: Live Feed
        st.header("Live Consensus Feed")
        render_live_feed(events, max_events=5)
