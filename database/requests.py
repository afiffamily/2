from sqlalchemy import select
from database.models import async_session, Movie
from database.models import User,Channel
from sqlalchemy import func

async def add_movie(kino_kodi: str, message_id: int):
    kino_kodi = str(kino_kodi).strip()
    print(f"📥 [DB SAQLASH] Kino kodi: '{kino_kodi}', Message ID: {message_id}")
    async with async_session() as session:
        movie = await session.scalar(select(Movie).where(Movie.kino_kodi == kino_kodi))
        if movie:
            movie.message_id = message_id
            print(f"🔄 [DB] Eski kino yangilandi: '{kino_kodi}'")
        else:
            session.add(Movie(kino_kodi=kino_kodi, message_id=message_id))
            print(f"✅ [DB] Yangi kino qo'shildi: '{kino_kodi}'")
            
        await session.commit()
        print(f"💾 [DB] Muvaffaqiyatli saqlandi!")
async def get_movie(kino_kodi: str):
    kino_kodi = str(kino_kodi).strip()
    print(f"🔍 [DB QIDIRUV] Qidirilayotgan kod: '{kino_kodi}'")
    async with async_session() as session:
        movie = await session.scalar(select(Movie).where(Movie.kino_kodi == kino_kodi))
        if movie:
            print(f"🎉 [DB] Topildi! Message ID: {movie.message_id}")
            return movie.message_id
        else:
            print(f"❌ [DB] Topilmadi!")
            return None

async def rate_movie(kino_kodi: str, action: str):
    kino_kodi = str(kino_kodi).strip()
    async with async_session() as session:
        movie = await session.scalar(select(Movie).where(Movie.kino_kodi == kino_kodi))
        if movie:
            if action == "like":
                movie.likes += 1
            elif action == "dislike":
                movie.dislikes += 1
            await session.commit()
            return True
        return False


async def add_user(telegram_id: int, full_name: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            session.add(User(telegram_id=telegram_id, full_name=full_name))
            await session.commit()
            print(f"👤 [YANGI USER] {full_name} ({telegram_id}) bazaga saqlandi!")
            return True
        return False    
    
    
async def get_statistics():
    async with async_session() as session:
        total_users = await session.scalar(select(func.count(User.id)))
        total_movies = await session.scalar(select(func.count(Movie.id)))
        top_movies = await session.scalars(select(Movie).order_by(Movie.likes.desc()).limit(3))
        return total_users or 0, total_movies or 0, top_movies.all()    
    
async def get_all_users():
    async with async_session() as session:
        users = await session.scalars(select(User))
        return users.all()    


async def get_all_channels():
    async with async_session() as session:
        channels = await session.scalars(select(Channel))
        return channels.all()

async def add_channel(channel_id: int, title: str, link: str):
    async with async_session() as session:
        channel = await session.scalar(select(Channel).where(Channel.channel_id == channel_id))
        if not channel:
            session.add(Channel(channel_id=channel_id, title=title, link=link))
            await session.commit()
            return True
        return False

async def delete_channel(channel_id: int):
    async with async_session() as session:
        channel = await session.scalar(select(Channel).where(Channel.channel_id == channel_id))
        if channel:
            await session.delete(channel)
            await session.commit()
            return True
        return False    
    
async def delete_movie_by_code(kino_kodi: str):
    async with async_session() as session:
        movie = await session.scalar(select(Movie).where(Movie.kino_kodi == kino_kodi))
        if movie:
            await session.delete(movie)
            await session.commit()
            return True
        return False    