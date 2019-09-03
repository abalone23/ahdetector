import sys
import re
import praw
import json
from datetime import datetime, timedelta
import datetime as dt
from psaw import PushshiftAPI
from pymongo import MongoClient
import os

api = PushshiftAPI()

start_epoch = '2019-08'
num_days = 70
# limit = 10000000

PRAW_CLIENT_SECRET = os.getenv('PRAW_CLIENT_SECRET')
PRAW_CLIENT_ID = os.getenv('PRAW_CLIENT_ID')
PRAW_USER_AGENT = os.getenv('PRAW_USER_AGENT')

reddit = praw.Reddit(client_id=PRAW_CLIENT_ID,
                     client_secret=PRAW_CLIENT_SECRET,
                     user_agent=PRAW_USER_AGENT)

# no a--holes here < 2018, no a-holes here > 2018
results_dict = {'asshole': 'YTA', 'not the a-hole': 'NTA', 'everyone sucks': 'ESH', 'no a-holes here': 'NAH',
                'no a--holes here': 'NAH', 'not enough info': 'INF'}

# convert unicode quotations and zero-with space
replace_list = (('\n', ' '), ('\u2018', "'"), ('\u2019', "'"), ('\u201c', '"'), ('\u201d', '"'), ("&#x200B;", ''))

def get_posts(subreddit, start, num_days):
    """
    Save posts and highest rated comment from a subreddit to a json file
    Args:
    subreddit (str): Subreddit
    limit (int): max posts to retrieve
    start: start date
    end: end date
    """

    start_epoch = int(datetime.strptime(start, '%Y-%m').timestamp())
    start_epoch_date = datetime.strptime(start, '%Y-%m')
    end_epoch_date = start_epoch_date + timedelta(days=num_days)
    end_epoch = int(end_epoch_date.timestamp())

    post_list = list(api.search_submissions(after=start_epoch, before=end_epoch,
                     subreddit=subreddit,
                     sort='asc',
                     stickied=False,
                     filter=['id']))

    posts = []
    prev_post_id = 0
    prev_post_date_y = ''
    prev_post_date_m = ''
    prev_post_date_d = ''

    for post in post_list:
        post_id = post[1]
        post_timestamp = int(post[0])
        post_date = datetime.fromtimestamp(post_timestamp).strftime('%Y-%m-%d')
        post_date_str = datetime.strptime(post_date, "%Y-%m-%d") 
        post_date_d = post_date_str.day        
        post_date_m = post_date_str.month
        post_date_y = post_date_str.year

        # Save json file for previous month:
        if post_date_m != prev_post_date_m and prev_post_date_m != '':
        # if post_date_d == 15:
            filename = subreddit.lower() + '_' + str(prev_post_date_y) + '_' + str(prev_post_date_m).zfill(2) + '.json'
            with open(filename, 'w') as fp:
                json.dump(posts, fp, indent=2)
                # sys.exit()
            posts = [] # reset posts list for new month

        submission = reddit.submission(id=post_id)
        post_score = submission.score
        post_permalink = submission.permalink
        post_num_comments = submission.num_comments
        post_link_flair = submission.link_flair_text
        if post_link_flair is not None:
            post_link_flair = post_link_flair.lower()

        post_title = submission.title
        for r in replace_list:
            post_title = post_title.replace(*r)
        post_title = re.sub(r'\s+', ' ', post_title).strip()

        post_question = submission.selftext # use question from praw api since psaw api may contain old/invalid data
        for r in replace_list:
            post_question = post_question.replace(*r)
        post_question = re.sub(r'\s+', ' ', post_question).strip()

        submission.comment_sort = 'top'
        submission.comment_limit = 2
        submission.comments.replace_more(limit=0)
        
        # some questions are [deleted] etc. so only include if question is > than 100 chars
        if len(post_question) > 100:
            for top_level_comment in submission.comments:
                # for some reason it's returning more than 2 comments per post even though comment_limit=2
                # so only process comment if it's new and is not stickied since it's sorted by top
                if top_level_comment.stickied == False and post_id != prev_post_id:
                    prev_post_id = post_id

                    top_comment_id = top_level_comment.id
                    top_comment_score = top_level_comment.score
                    top_comment = top_level_comment.body
                    for r in replace_list:
                        top_comment = top_comment.replace(*r)
                    top_comment = re.sub(r'\s+', ' ', top_comment).strip()

                    print(post_link_flair)
                    # only include observations with a valid label:
                    if post_link_flair == 'asshole' or post_link_flair == 'not the a-hole' or post_link_flair == 'everyone sucks' or \
                        post_link_flair == 'no a-holes here' or post_link_flair == 'no a--holes here' or post_link_flair == 'not enough info':
                        print(post_date_y, post_date_m, post_date_d, post_id, post_link_flair, post_title)

                        posts.append({
                            'post_id': post_id,
                            'post_title': post_title,
                            'post_timestamp': post_timestamp,
                            'post_permalink': post_permalink,
                            'post_score': post_score,
                            'post_num_comments': post_num_comments,
                            'post_question': post_question,
                            'top_comment_id': top_comment_id,
                            'top_comment_score': top_comment_score,
                            'top_comment': top_comment,
                            'post_result': results_dict[post_link_flair]
                        })

        prev_post_date_d = post_date_d        
        prev_post_date_m = post_date_m
        prev_post_date_y = post_date_y

get_posts('AmItheAsshole', start_epoch, num_days)