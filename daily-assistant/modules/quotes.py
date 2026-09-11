"""
Daily Quotes Module for Obsidian Daily Assistant
Provides a curated catalog of profound quotes on Stoicism, discipline,
physical resilience, deep focus, and purposeful living.
Deterministic selection based on date ensures consistency across multiple runs for the same day.
"""

from datetime import date
from typing import Dict, Optional

QUOTES = [
    # Stoicism & Mindset
    {
        "quote": "You have power over your mind - not outside events. Realize this, and you will find strength.",
        "author": "Marcus Aurelius",
        "theme": "Inner Strength"
    },
    {
        "quote": "We suffer more often in imagination than in reality.",
        "author": "Seneca",
        "theme": "Clarity & Stoicism"
    },
    {
        "quote": "No man is free who is not master of himself.",
        "author": "Epictetus",
        "theme": "Self-Mastery"
    },
    {
        "quote": "Waste no more time arguing what a good man should be. Be one.",
        "author": "Marcus Aurelius",
        "theme": "Action Over Words"
    },
    {
        "quote": "The impediment to action advances action. What stands in the way becomes the way.",
        "author": "Marcus Aurelius",
        "theme": "Resilience"
    },
    {
        "quote": "He who fears death will never do anything worth of a man who is alive.",
        "author": "Seneca",
        "theme": "Courage"
    },
    {
        "quote": "First say to yourself what you would be; and then do what you have to do.",
        "author": "Epictetus",
        "theme": "Identity & Discipline"
    },
    {
        "quote": "Luck is what happens when preparation meets opportunity.",
        "author": "Seneca",
        "theme": "Preparedness"
    },
    {
        "quote": "If you want to improve, be content to be thought foolish and stupid.",
        "author": "Epictetus",
        "theme": "Humility & Growth"
    },
    {
        "quote": "It is not that we have a short time to live, but that we waste a lot of it.",
        "author": "Seneca",
        "theme": "Time Stewardship"
    },
    {
        "quote": "The soul becomes dyed with the color of its thoughts.",
        "author": "Marcus Aurelius",
        "theme": "Mindset"
    },
    {
        "quote": "Begin at once to live, and count each separate day as a new life.",
        "author": "Seneca",
        "theme": "Presence"
    },
    {
        "quote": "Curb your desire—don't set your heart on so many things and you will get what you need.",
        "author": "Epictetus",
        "theme": "Focus"
    },
    {
        "quote": "When you arise in the morning think of what a privilege it is to be alive, to think, to enjoy, to love.",
        "author": "Marcus Aurelius",
        "theme": "Gratitude"
    },
    {
        "quote": "Associate with people who are likely to improve you.",
        "author": "Seneca",
        "theme": "Environment"
    },

    # Habits, Discipline & Execution
    {
        "quote": "We are what we repeatedly do. Excellence, then, is not an act, but a habit.",
        "author": "Will Durant",
        "theme": "Habit & Consistency"
    },
    {
        "quote": "You do not rise to the level of your goals. You fall to the level of your systems.",
        "author": "James Clear",
        "theme": "Systems Over Goals"
    },
    {
        "quote": "Small disciplines repeated with consistency every day lead to great achievements gained slowly over time.",
        "author": "John C. Maxwell",
        "theme": "Consistency"
    },
    {
        "quote": "Discipline equals freedom.",
        "author": "Jocko Willink",
        "theme": "Discipline"
    },
    {
        "quote": "Amateurs sit and wait for inspiration, the rest of us just get up and go to work.",
        "author": "Stephen King",
        "theme": "Work Ethic"
    },
    {
        "quote": "Clarity precedes mastery. Commit to doing the essential few things exceptionally well.",
        "author": "Robin Sharma",
        "theme": "Essentialism"
    },
    {
        "quote": "What we fear doing most is usually what we most need to do.",
        "author": "Tim Ferriss",
        "theme": "Courage in Action"
    },
    {
        "quote": "If you don't design your own life plan, chances are you'll fall into someone else's plan.",
        "author": "Jim Rohn",
        "theme": "Intentional Living"
    },
    {
        "quote": "Action is the foundational key to all success.",
        "author": "Pablo Picasso",
        "theme": "Execution"
    },
    {
        "quote": "It is not enough to be busy. The question is: what are we busy about?",
        "author": "Henry David Thoreau",
        "theme": "Purposeful Focus"
    },
    {
        "quote": "Continuous effort—not strength or intelligence—is the key to unlocking our potential.",
        "author": "Winston Churchill",
        "theme": "Perseverance"
    },
    {
        "quote": "Your net worth to the world is usually determined by what remains after your bad habits are subtracted from your good ones.",
        "author": "Benjamin Franklin",
        "theme": "Self-Reflection"
    },
    {
        "quote": "Energy flows where attention goes.",
        "author": "Tony Robbins",
        "theme": "Attention & Focus"
    },
    {
        "quote": "Either you run the day, or the day runs you.",
        "author": "Jim Rohn",
        "theme": "Daily Ownership"
    },
    {
        "quote": "Motivation is what gets you started. Habit is what keeps you going.",
        "author": "Jim Ryun",
        "theme": "Habit Formation"
    },

    # Deep Work, Focus & Craftsmanship
    {
        "quote": "The ability to perform deep work is becoming increasingly rare at exactly the same time it is becoming increasingly valuable in our economy.",
        "author": "Cal Newport",
        "theme": "Deep Work"
    },
    {
        "quote": "Simplicity is the ultimate sophistication.",
        "author": "Leonardo da Vinci",
        "theme": "Simplicity"
    },
    {
        "quote": "Focus is a matter of deciding what things you're not going to do.",
        "author": "John Carmack",
        "theme": "Ruthless Prioritization"
    },
    {
        "quote": "Do less, but do it with the complete focus of your entire being.",
        "author": "Marcus Aurelius",
        "theme": "Deliberate Practice"
    },
    {
        "quote": "Details make perfection, and perfection is not a detail.",
        "author": "Leonardo da Vinci",
        "theme": "Craftsmanship"
    },
    {
        "quote": "Quality is not an act, it is a habit.",
        "author": "Aristotle",
        "theme": "Standard of Excellence"
    },
    {
        "quote": "Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away.",
        "author": "Antoine de Saint-Exupéry",
        "theme": "Minimalism"
    },
    {
        "quote": "The secret of getting ahead is getting started.",
        "author": "Mark Twain",
        "theme": "Momentum"
    },
    {
        "quote": "The successful warrior is the average man, with laser-like focus.",
        "author": "Bruce Lee",
        "theme": "Focus"
    },
    {
        "quote": "You can do anything, but not everything.",
        "author": "David Allen",
        "theme": "Capacity & Prioritization"
    },

    # Physical Vitality, Health & Movement
    {
        "quote": "No citizen has a right to be an amateur in the matter of physical training. What a disgrace it is for a man to grow old without seeing the beauty and strength of which his body is capable.",
        "author": "Socrates",
        "theme": "Physical Vitality"
    },
    {
        "quote": "Take care of your body. It's the only place you have to live.",
        "author": "Jim Rohn",
        "theme": "Health Stewardship"
    },
    {
        "quote": "A champion is someone who gets up when they can't.",
        "author": "Jack Dempsey",
        "theme": "Grit"
    },
    {
        "quote": "The body achieves what the mind believes.",
        "author": "Napoleon Hill",
        "theme": "Mental Toughness"
    },
    {
        "quote": "Strength does not come from physical capacity. It comes from an indomitable will.",
        "author": "Mahatma Gandhi",
        "theme": "Willpower"
    },
    {
        "quote": "To enjoy good health, to bring true happiness to one's family, to bring peace to all, one must first discipline and control one's own mind.",
        "author": "Buddha",
        "theme": "Holistic Health"
    },
    {
        "quote": "Physical fitness is the first requisite of happiness.",
        "author": "Joseph Pilates",
        "theme": "Physical Baseline"
    },
    {
        "quote": "It is exercise alone that supports the spirits, and keeps the mind in vigor.",
        "author": "Marcus Tullius Cicero",
        "theme": "Movement & Mental Health"
    },
    {
        "quote": "Today I will do what others won't, so tomorrow I can accomplish what others can't.",
        "author": "Jerry Rice",
        "theme": "Athletic Mindset"
    },
    {
        "quote": "The pain you feel today will be the strength you feel tomorrow.",
        "author": "Arnold Schwarzenegger",
        "theme": "Rebuilding Strength"
    },

    # Resilience & Overcoming Adversity
    {
        "quote": "Everything can be taken from a man but one thing: the last of the human freedoms—to choose one's attitude in any given set of circumstances.",
        "author": "Viktor E. Frankl",
        "theme": "Attitude & Freedom"
    },
    {
        "quote": "It is not the critic who counts... The credit belongs to the man who is actually in the arena, whose face is marred by dust and sweat and blood.",
        "author": "Theodore Roosevelt",
        "theme": "The Arena"
    },
    {
        "quote": "Do not pray for an easy life, pray for the strength to endure a difficult one.",
        "author": "Bruce Lee",
        "theme": "Endurance"
    },
    {
        "quote": "Fall seven times and stand up eight.",
        "author": "Japanese Proverb",
        "theme": "Tenacity"
    },
    {
        "quote": "The greatest glory in living lies not in never falling, but in rising every time we fall.",
        "author": "Nelson Mandela",
        "theme": "Rising Up"
    },
    {
        "quote": "Hardships often prepare ordinary people for an extraordinary destiny.",
        "author": "C.S. Lewis",
        "theme": "Perspective"
    },
    {
        "quote": "In the depth of winter, I finally learned that within me there lay an invincible summer.",
        "author": "Albert Camus",
        "theme": "Inner Resilience"
    },
    {
        "quote": "Out of difficulties grow miracles.",
        "author": "Jean de La Bruyère",
        "theme": "Transformation"
    },
    {
        "quote": "He who has a why to live can bear almost any how.",
        "author": "Friedrich Nietzsche",
        "theme": "Purpose"
    },
    {
        "quote": "Rock bottom became the solid foundation on which I rebuilt my life.",
        "author": "J.K. Rowling",
        "theme": "Rebuilding"
    },

    # Wisdom, Clarity & Perspective
    {
        "quote": "A journey of a thousand miles begins with a single step.",
        "author": "Lao Tzu",
        "theme": "First Steps"
    },
    {
        "quote": "Knowing yourself is the beginning of all wisdom.",
        "author": "Aristotle",
        "theme": "Self-Awareness"
    },
    {
        "quote": "Simplicity, clarity, singularity: These are the attributes that give our lives power and vividness and joy.",
        "author": "Richard Foster",
        "theme": "Clarity"
    },
    {
        "quote": "Be tolerant with others and strict with yourself.",
        "author": "Marcus Aurelius",
        "theme": "Equanimity"
    },
    {
        "quote": "When we are no longer able to change a situation, we are challenged to change ourselves.",
        "author": "Viktor E. Frankl",
        "theme": "Adaptability"
    },
    {
        "quote": "Adopt the pace of nature: her secret is patience.",
        "author": "Ralph Waldo Emerson",
        "theme": "Patience"
    },
    {
        "quote": "The unexamined life is not worth living.",
        "author": "Socrates",
        "theme": "Reflection"
    },
    {
        "quote": "Do not let what you cannot do interfere with what you can do.",
        "author": "John Wooden",
        "theme": "Control the Controllables"
    },
    {
        "quote": "In the middle of difficulty lies opportunity.",
        "author": "Albert Einstein",
        "theme": "Perspective"
    },
    {
        "quote": "Silence is a source of great strength.",
        "author": "Lao Tzu",
        "theme": "Calm & Equanimity"
    },
    {
        "quote": "The only true wisdom is in knowing you know nothing.",
        "author": "Socrates",
        "theme": "Intellectual Humility"
    },
    {
        "quote": "Peace comes from within. Do not seek it without.",
        "author": "Buddha",
        "theme": "Inner Peace"
    },
    {
        "quote": "Life is what happens when you're busy making other plans.",
        "author": "John Lennon",
        "theme": "Presence"
    },
    {
        "quote": "To know what you know and that you do not know what you do not know, that is true knowledge.",
        "author": "Confucius",
        "theme": "Wisdom"
    },
    {
        "quote": "Give me six hours to chop down a tree and I will spend the first four sharpening the axe.",
        "author": "Abraham Lincoln",
        "theme": "Preparation"
    },

    # Purpose, Leadership & Daily Impact
    {
        "quote": "Your time is limited, so don't waste it living someone else's life.",
        "author": "Steve Jobs",
        "theme": "Authenticity"
    },
    {
        "quote": "Whatever you are, be a good one.",
        "author": "Abraham Lincoln",
        "theme": "Dedication"
    },
    {
        "quote": "The best way to predict the future is to create it.",
        "author": "Peter Drucker",
        "theme": "Proactivity"
    },
    {
        "quote": "Act as if what you do makes a difference. It does.",
        "author": "William James",
        "theme": "Impact"
    },
    {
        "quote": "Nothing in this world can take the place of persistence.",
        "author": "Calvin Coolidge",
        "theme": "Persistence"
    },
    {
        "quote": "The future depends on what you do today.",
        "author": "Mahatma Gandhi",
        "theme": "Today's Action"
    },
    {
        "quote": "Believe you can and you're halfway there.",
        "author": "Theodore Roosevelt",
        "theme": "Belief"
    },
    {
        "quote": "Great things are done by a series of small things brought together.",
        "author": "Vincent van Gogh",
        "theme": "Compounding Effort"
    },
    {
        "quote": "The man who moves a mountain begins by carrying away small stones.",
        "author": "Confucius",
        "theme": "Incremental Progress"
    },
    {
        "quote": "Opportunities multiply as they are seized.",
        "author": "Sun Tzu",
        "theme": "Seizing Initiative"
    },
    {
        "quote": "Courage is not the absence of fear, but rather the assessment that something else is more important than fear.",
        "author": "Franklin D. Roosevelt",
        "theme": "Courage"
    },
    {
        "quote": "What lies behind us and what lies before us are tiny matters compared to what lies within us.",
        "author": "Ralph Waldo Emerson",
        "theme": "Inner Capacity"
    },
    {
        "quote": "Keep your face always toward the sunshine—and shadows will fall behind you.",
        "author": "Walt Whitman",
        "theme": "Optimism"
    },
    {
        "quote": "Live as if you were to die tomorrow. Learn as if you were to live forever.",
        "author": "Mahatma Gandhi",
        "theme": "Continuous Learning"
    },
    {
        "quote": "To live is the rarest thing in the world. Most people exist, that is all.",
        "author": "Oscar Wilde",
        "theme": "Living Fully"
    },
    {
        "quote": "Doubt kills more dreams than failure ever will.",
        "author": "Suzy Kassem",
        "theme": "Confidence"
    },
    {
        "quote": "If you want to lift yourself up, lift up someone else.",
        "author": "Booker T. Washington",
        "theme": "Generosity"
    },
    {
        "quote": "You miss 100% of the shots you don't take.",
        "author": "Wayne Gretzky",
        "theme": "Initiative"
    },
    {
        "quote": "Strive not to be a success, but rather to be of value.",
        "author": "Albert Einstein",
        "theme": "Value Creation"
    },
    {
        "quote": "Don't count the days, make the days count.",
        "author": "Muhammad Ali",
        "theme": "Urgency & Purpose"
    },
    {
        "quote": "The mind is everything. What you think you become.",
        "author": "Buddha",
        "theme": "Mindset Mastery"
    },
    {
        "quote": "Definiteness of purpose is the starting point of all achievement.",
        "author": "W. Clement Stone",
        "theme": "Purpose"
    },
    {
        "quote": "An unexamined day is a day not truly lived. Reflect, adjust, and conquer tomorrow.",
        "author": "Stoic Maxim",
        "theme": "Daily Reflection"
    },
    {
        "quote": "Mastering others is strength. Mastering yourself is true power.",
        "author": "Lao Tzu",
        "theme": "Self-Mastery"
    },
    {
        "quote": "How we spend our days is, of course, how we spend our lives.",
        "author": "Annie Dillard",
        "theme": "Daily Intentionality"
    }
]

def get_daily_quote(target_date: Optional[date] = None) -> Dict[str, str]:
    """
    Returns a deterministic daily quote based on the target date.
    Uses target_date.toordinal() so that running multiple times on the same date
    always produces the identical quote, while rotating seamlessly every day.
    """
    if target_date is None:
        target_date = date.today()

    # Deterministic index based on date ordinal
    index = target_date.toordinal() % len(QUOTES)
    selected = QUOTES[index]
    return {
        "quote": selected["quote"],
        "author": selected["author"],
        "theme": selected["theme"],
        "formatted": f'> 💭 *"{selected["quote"]}"*\n> — **{selected["author"]}**'
    }

if __name__ == "__main__":
    today = date.today()
    q = get_daily_quote(today)
    print(f"Daily Quote for {today}:")
    print(q["formatted"])
