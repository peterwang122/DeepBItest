import pymysql
from ad_api.api import sponsored_products
from ad_api.base import Marketplaces
import json
import datetime
from decimal import Decimal

my_credentials = dict(
        refresh_token='****',
        client_id='****',
        client_secret='****',
        profile_id='****',
    )

class CampaignTools:
    def __init__(self):
        self.my_credentials = dict(
        refresh_token='****',
        client_id='****',
        client_secret='****',
        profile_id='****',
    )

    # 新建广告活动/系列
    def create_campaigns_api(self,campaign_info):
        try:
            result = sponsored_products.CampaignsV3(credentials=my_credentials,
                                                    marketplace=Marketplaces.NA,
                                                    debug=True).create_campaigns(
                body=json.dumps(campaign_info))
        except Exception as e:
            print("create campaign failed: ", e)
            result = None
        compaignID = ""
        if result and result.payload["campaigns"]["success"]:
            campaignID = result.payload["campaigns"]["success"][0]["campaignId"]
            print("create campaign success, compaignID is ", compaignID)
            res = ["success",campaignID]
        else:
            print(" create campaign failed:")
            res = ["failed",""]
        # 返回创建的 compaignID
        return res

    # 更新广告系列（调整Budget、状态、enddate）
    def update_campaigns(self,campaign_info):

        try:
            result = sponsored_products.CampaignsV3(credentials=my_credentials,
                                                    marketplace=Marketplaces.NA,
                                                    debug=True).edit_campaigns(
                body=json.dumps(campaign_info))
            print(result)
        except Exception as e:
            print("update campaigns failed: ", e)
            result = None
        compaignID = ""
        if result and result.payload["campaigns"]["success"]:
            campaignID = result.payload["campaigns"]["success"][0]["campaignId"]
            print("update campaigns success, compaignID is ", compaignID)
            res = ["success", campaignID]
        else:
            print(" update campaigns failed:")
            res = ["failed", ""]
        # 返回创建的 compaignID
        return res

    # 给广告系列增加否定关键词
    def add_campaigns_negative_keywords(self,campaign_negativekv_info):

        try:
            result = sponsored_products.CampaignNegativeKeywordsV3(credentials=my_credentials,
                                                    marketplace=Marketplaces.NA,
                                                    debug=True).create_campaign_negative_keywords(
                body=json.dumps(campaign_negativekv_info))
            print(result)
        except Exception as e:
            print("add campaign negative keyword failed: ", e)
            result = None
        if result and result.payload["campaignNegativeKeywords"]["success"]:
            campaignNegativeKeywordId = result.payload["campaignNegativeKeywords"]["success"][0]["campaignNegativeKeywordId"]
            print("add campaign negative keyword success, campaignNegativeKeywordId is ", campaignNegativeKeywordId)
            res = ["success", campaignNegativeKeywordId]
        else:
            print(" add campaign negative keyword failed")
            res = ["failed", ""]
        # 返回创建的 campaignNegativeKeywordId
        return res


    # 给广告系列更新否定关键词
    def update_campaigns_negative_keywords(self,campaign_negativekv_info):

        try:
            result = sponsored_products.CampaignNegativeKeywordsV3(credentials=my_credentials,
                                                    marketplace=Marketplaces.NA,
                                                    debug=True).edit_campaign_negative_keywords(
                body=json.dumps(campaign_negativekv_info))
            print(result)
        except Exception as e:
            print("更新广告系列否定关键词失败: ", e)
            result = None
        if result and result.payload["campaignNegativeKeywords"]["success"]:
            campaignNegativeKeywordId = result.payload["campaignNegativeKeywords"]["success"][0]["campaignNegativeKeywordId"]
            print("更新广告系列否定关键词成功:campaignNegativeKeywordId is ", campaignNegativeKeywordId)
            res = ["success", campaignNegativeKeywordId]
        else:
            print(" xxxx 更新广告系列否定关键词失败:")
            res = ["failed", ""]
        # 返回创建的 campaignNegativeKeywordId
        return res

# 更新广告关键词测试
# campaign_negativekv_info = {
#   "campaignNegativeKeywords": [
#     {
#       "keywordId": "496300953645062",
#       "state": "PAUSED"
#     }
#   ]
# }
# ct=CampaignTools()
# res = ct.update_campaigns_negative_keywords(campaign_negativekv_info)
# print(res)

# 测试 新增广告系列的否定关键词
# campaign_negativekv_info={
#   "campaignNegativeKeywords": [
#     {
#       "campaignId": "531571979684792",
#       "matchType": "NEGATIVE_PHRASE",
#       "state": "ENABLED",
#       "keywordText": "addtest0508"
#     }
#   ]
# }
# ct=CampaignTools()
# res = ct.add_campaigns_negative_keywords(campaign_negativekv_info)
# print(res)

    def get_campaigns_negative_keywords(self,campaign_info):
        try:
            result = sponsored_products.CampaignNegativeKeywordsV3(credentials=my_credentials,
                                                    marketplace=Marketplaces.NA,
                                                    debug=True).list_campaign_negative_keywords(
                body=json.dumps(campaign_info))
            print(result)
        except Exception as e:
            print("get广告系列否定关键词失败: ", e)
            result = None
        if result and result.payload["campaignNegativeKeywords"]:
            campaignNegativeKeywordId = result.payload["campaignNegativeKeywords"]
            print("get广告系列否定关键词成功:campaignNegativeKeywordId is ", campaignNegativeKeywordId)
            res = ["success", campaignNegativeKeywordId]
        else:
            print(" xxxx get广告系列否定关键词失败:")
            res = ["failed", ""]
        # 返回创建的 campaignNegativeKeywordId
        return res

# ct=CampaignTools()
# 测试更新广告系列信息
# res = ct.update_campaigns(campaign_info)
# print(type(res))
# print(res)


# 测试新增广告系列

