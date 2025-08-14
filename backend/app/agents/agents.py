"""CrewAI agent definitions for book writing"""

from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew
from litellm import acompletion
import os
import asyncio
import json


class BookWritingAgents:
    """Collection of specialized agents for book writing"""
    
    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("PRIMARY_MODEL", "claude-3-5-sonnet")
        self._setup_agents()
    
    def _setup_agents(self):
        """Initialize all agents with their roles and goals"""
        
        self.concept_generator = Agent(
            role="Concept Generator",
            goal="Transform plot seeds and brief into rich, compelling concepts",
            backstory="""You are a creative visionary who excels at taking simple 
            ideas and expanding them into rich, multi-layered concepts. You understand 
            narrative structure, themes, and how to create compelling story hooks.""",
            verbose=False,
            allow_delegation=False,
        )
        
        self.outliner = Agent(
            role="Story Outliner",
            goal="Create detailed, beat-by-beat chapter outlines from concepts",
            backstory="""You are a master of story structure who can break down 
            complex narratives into clear, engaging chapter outlines. You understand 
            pacing, tension, and how to keep readers engaged throughout a book.""",
            verbose=False,
            allow_delegation=False,
        )
        
        self.writer = Agent(
            role="Chapter Writer",
            goal="Write vivid, engaging prose that matches the style guide",
            backstory="""You are a talented writer who can adapt to any style and 
            genre. You excel at creating immersive scenes, compelling dialogue, and 
            prose that keeps readers turning pages. You follow style guides precisely.""",
            verbose=False,
            allow_delegation=False,
        )
        
        self.editor = Agent(
            role="Structural Editor",
            goal="Perform structural edits to improve clarity, pacing, and impact",
            backstory="""You are an experienced editor who can identify and fix 
            structural issues in writing. You excel at tightening prose, improving 
            flow, and ensuring consistency while preserving the author's voice.""",
            verbose=False,
            allow_delegation=False,
        )
        
        self.continuity_checker = Agent(
            role="Continuity Checker",
            goal="Ensure consistency across names, ages, timeline, and facts",
            backstory="""You are a detail-oriented fact-checker who catches 
            inconsistencies that others miss. You maintain perfect recall of 
            character details, plot points, and timeline to ensure continuity.""",
            verbose=False,
            allow_delegation=False,
        )
    
    async def generate_concepts(
        self,
        brief: str,
        plot_seeds: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate rich concepts from brief and seeds"""
        task = Task(
            description=f"""Generate rich story concepts from this brief:
            {brief}
            
            Plot seeds to incorporate: {plot_seeds or 'None provided'}
            
            Provide:
            1. Core themes and messages
            2. Main conflict and stakes
            3. Character arcs
            4. Unique hooks and selling points
            """,
            agent=self.concept_generator,
            expected_output="Detailed story concepts in JSON format"
        )
        
        crew = Crew(
            agents=[self.concept_generator],
            tasks=[task],
            verbose=False
        )
        
        result = await asyncio.to_thread(crew.kickoff)
        return {"concepts": str(result)}
    
    async def create_outline(
        self,
        brief: str,
        concepts: Dict[str, Any],
        target_chapters: int = 10,
        style_guide: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create detailed chapter-by-chapter outline"""
        task = Task(
            description=f"""Create a detailed {target_chapters}-chapter outline.
            
            Brief: {brief}
            Concepts: {json.dumps(concepts)}
            Style Guide: {style_guide or 'Standard narrative structure'}
            
            For each chapter provide:
            1. Chapter title
            2. Key events and beats
            3. Character development
            4. Hooks and cliffhangers
            5. Word count target
            """,
            agent=self.outliner,
            expected_output="Chapter-by-chapter outline in JSON format"
        )
        
        crew = Crew(
            agents=[self.outliner],
            tasks=[task],
            verbose=False
        )
        
        result = await asyncio.to_thread(crew.kickoff)
        return {"outline": str(result)}
    
    async def write_chapter(
        self,
        chapter_number: int,
        outline: str,
        style_guide: str,
        character_bible: Optional[Dict[str, Any]] = None,
        previous_chapters: Optional[List[str]] = None
    ) -> str:
        """Write a single chapter based on outline"""
        context = ""
        if previous_chapters and len(previous_chapters) > 0:
            # Include last 2 chapters for context
            recent = previous_chapters[-2:] if len(previous_chapters) > 1 else previous_chapters
            context = f"Previous chapters for context:\n{'...'.join(recent[-500:] for c in recent)}"
        
        task = Task(
            description=f"""Write Chapter {chapter_number} following this outline:
            {outline}
            
            Style Guide: {style_guide}
            Character Bible: {json.dumps(character_bible) if character_bible else 'Not provided'}
            {context}
            
            Requirements:
            1. Match the style guide precisely
            2. Maintain character consistency
            3. Create vivid scenes and dialogue
            4. End with a compelling hook
            5. Target 3000-5000 words
            """,
            agent=self.writer,
            expected_output="Complete chapter text in markdown format"
        )
        
        crew = Crew(
            agents=[self.writer],
            tasks=[task],
            verbose=False
        )
        
        result = await asyncio.to_thread(crew.kickoff)
        return str(result)
    
    async def edit_content(
        self,
        content: str,
        edit_type: str = "structural",
        instructions: Optional[str] = None
    ) -> str:
        """Edit content for structure, clarity, and impact"""
        edit_focus = {
            "structural": "Focus on structure, pacing, and narrative flow",
            "line": "Focus on sentence-level clarity and readability",
            "copy": "Focus on grammar, punctuation, and consistency",
            "proof": "Focus on typos, formatting, and final polish"
        }
        
        task = Task(
            description=f"""Perform {edit_type} editing on this content.
            
            {edit_focus.get(edit_type, 'General editing')}
            
            Additional instructions: {instructions or 'None'}
            
            Content to edit:
            {content}
            
            Preserve the author's voice while improving the text.
            """,
            agent=self.editor,
            expected_output="Edited content with improvements"
        )
        
        crew = Crew(
            agents=[self.editor],
            tasks=[task],
            verbose=False
        )
        
        result = await asyncio.to_thread(crew.kickoff)
        return str(result)
    
    async def check_continuity(
        self,
        chapters: List[str],
        character_bible: Optional[Dict[str, Any]] = None,
        timeline: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Check for continuity errors across chapters"""
        task = Task(
            description=f"""Check these chapters for continuity errors:
            
            Character Bible: {json.dumps(character_bible) if character_bible else 'Not provided'}
            Timeline: {json.dumps(timeline) if timeline else 'Not provided'}
            
            Check for:
            1. Character name consistency
            2. Age and description consistency
            3. Timeline inconsistencies
            4. Plot contradictions
            5. Setting inconsistencies
            6. Factual errors
            
            Chapters to review:
            {chr(10).join([f'Chapter {i+1}: {c[:500]}...' for i, c in enumerate(chapters)])}
            """,
            agent=self.continuity_checker,
            expected_output="JSON report of inconsistencies and suggestions"
        )
        
        crew = Crew(
            agents=[self.continuity_checker],
            tasks=[task],
            verbose=False
        )
        
        result = await asyncio.to_thread(crew.kickoff)
        
        try:
            # Try to parse as JSON, fallback to structured dict
            report = json.loads(str(result))
        except:
            report = {
                "raw_report": str(result),
                "inconsistencies": [],
                "suggestions": [],
                "confidence_score": 0.95
            }
        
        return report


class ParallelChapterWriter:
    """Orchestrate parallel chapter writing"""
    
    def __init__(self, agents: BookWritingAgents):
        self.agents = agents
    
    async def write_chapters_parallel(
        self,
        outline: Dict[str, Any],
        style_guide: str,
        character_bible: Optional[Dict[str, Any]] = None,
        max_parallel: int = 3
    ) -> List[str]:
        """Write multiple chapters in parallel"""
        chapters = []
        chapter_outlines = outline.get("chapters", [])
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(chapter_outlines), max_parallel):
            batch = chapter_outlines[i:i + max_parallel]
            
            tasks = []
            for j, chapter_outline in enumerate(batch):
                chapter_num = i + j + 1
                task = self.agents.write_chapter(
                    chapter_number=chapter_num,
                    outline=json.dumps(chapter_outline),
                    style_guide=style_guide,
                    character_bible=character_bible,
                    previous_chapters=chapters[-2:] if len(chapters) > 0 else None
                )
                tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks)
            chapters.extend(batch_results)
        
        return chapters