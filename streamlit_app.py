import streamlit as st
from google import genai
from pydantic import BaseModel


# -------------------------
# データの形を決める
# -------------------------
class Recipe(BaseModel):
    recipe_name: str
    feature: str
    ingredients: list[str]
    seasonings: list[str]
    steps: list[str]
    cooking_time: str


class RecipeSet(BaseModel):
    recipes: list[Recipe]


# -------------------------
# 画面設定
# -------------------------
st.set_page_config(page_title="AIレシピ比較メーカー", page_icon="🍳")

st.title("🍳 AIレシピ比較メーカー")
st.write("料理名を入力すると、Geminiが特徴の異なる5つのレシピを作り、違いを比較します。")


dish_name = st.text_input(
    "料理名を入力してください",
    placeholder="例：肉じゃが、親子丼、ミネストローネ",
)


if st.button("5つのレシピを比較する", type="primary"):
    if not dish_name.strip():
        st.warning("料理名を入力してください。")
        st.stop()

    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)

        recipe_prompt = f"""
あなたは家庭料理に詳しい料理研究家です。
「{dish_name}」について、特徴がはっきり異なるレシピを必ず5種類作ってください。

5種類は、できるだけ次のように方向性を変えてください。
1. 定番
2. 甘め
3. さっぱり
4. 時短
5. コク重視

料理によって上の分類が不自然な場合は、その料理に合う別の5分類に置き換えて構いません。
ただし、5種類の違いが明確に分かるようにしてください。

各レシピには必ず以下を含めてください。
・レシピ名
・特徴
・材料
・調味料
・作り方
・調理時間

材料と調味料には、家庭で再現できる具体的な分量を入れてください。
作り方は、初心者でも分かる順番で書いてください。
必ず5レシピだけを返してください。
"""

        with st.spinner("5つのレシピを作成しています..."):
            recipe_response = client.interactions.create(
                model="gemini-3.7-flash",
                input=recipe_prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": RecipeSet.model_json_schema(),
                },
            )

            recipe_set = RecipeSet.model_validate_json(recipe_response.output_text)

        if len(recipe_set.recipes) != 5:
            st.error("5つのレシピを生成できませんでした。もう一度お試しください。")
            st.stop()

        st.subheader(f"「{dish_name}」の5つのレシピ")

        for index, recipe in enumerate(recipe_set.recipes, start=1):
            with st.container(border=True):
                st.markdown(f"### レシピ{index}：{recipe.recipe_name}")
                st.markdown(f"**特徴**  \n{recipe.feature}")
                st.markdown(f"**調理時間**  \n{recipe.cooking_time}")

                st.markdown("**材料**")
                for item in recipe.ingredients:
                    st.markdown(f"- {item}")

                st.markdown("**調味料**")
                for item in recipe.seasonings:
                    st.markdown(f"- {item}")

                st.markdown("**作り方**")
                for step_number, step in enumerate(recipe.steps, start=1):
                    st.markdown(f"{step_number}. {step}")

        analysis_prompt = f"""
次の「{dish_name}」の5つのレシピを比較してください。

以下の観点で、初心者にも分かる日本語で整理してください。
・主な材料の違い
・調味料の違い
・味の方向性
・調理方法の違い
・調理時間
・それぞれどんな人に向いているか

最後に、5種類の特徴を短く一覧でまとめてください。

レシピデータ：
{recipe_response.output_text}
"""

        with st.spinner("5つのレシピの違いを分析しています..."):
            analysis_response = client.interactions.create(
                model="gemini-3.7-flash",
                input=analysis_prompt,
            )

        st.divider()
        st.header("5つのレシピの違い")
        st.markdown(analysis_response.output_text)

    except KeyError:
        st.error(
            "Gemini APIキーが設定されていません。Streamlit Secretsに "
            "GEMINI_API_KEY を登録してください。"
        )
    except Exception as e:
        st.error("エラーが発生しました。APIキーや通信状態を確認して、もう一度お試しください。")
        with st.expander("エラーの詳細"):
            st.code(str(e))
