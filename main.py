import urllib.parse
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    "astrbot_plugin_pollinations_images",
    "qa296",
    "使用 Pollinations AI生成图片。无需注册，开箱即用！",
    "1.2.0"
)
class PollinationsGeneratorPlugin(Star):
    """
    一个通过调用LLM生成英文提示词，并使用Pollinations AI服务的图片生成插件。
    """
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("花粉AI图片生成插件已加载。")

    async def generate_prompt_via_llm(self, theme: str) -> str:
        """
        通过 LLM 生成图片提示词的独立函数。

        Args:
            theme (str): 用户输入的主题

        Returns:
            str: 生成的英文提示词
        """
        provider = self.context.get_using_provider()
        if not provider:
            logger.warning("未找到可用的LLM服务，无法生成提示词。")
            raise Exception("未配置或启用任何大语言模型服务。")

        system_prompt_for_refinement = (
            "You are an expert in crafting prompts for AI image generation models. "
            "Your task is to take a user's simple idea and transform it into a rich, detailed, and artistic prompt in English. "
            "The final output should be a single, continuous string of keywords and descriptions, separated by commas. "
            "Do not add any other explanatory text, just the prompt itself. "
            "Focus on visual details, art style (e.g., photorealistic, watercolor, anime), composition, and lighting."
        )

        user_prompt_for_llm = f"User's idea: {theme}"

        llm_response = await provider.text_chat(
            prompt=user_prompt_for_llm,
            system_prompt=system_prompt_for_refinement,
            contexts=[]
        )

        if not llm_response or not llm_response.completion_text:
            logger.error("LLM未能返回有效的提示词。")
            raise Exception("生成提示词失败，请稍后再试。")

        return llm_response.completion_text.strip()

    @filter.llm_tool(name="generate_image_with_theme")
    async def generate_image_tool(self, event: AstrMessageEvent, theme: str):
        """
        LLM 函数调用工具：根据主题生成图片。

        Args:
            theme(string): 图片的详细描述
        """
        try:
            # 调用独立的 LLM 提示词生成函数
            refined_prompt = await self.generate_prompt_via_llm(theme)

            encoded_prompt = urllib.parse.quote(refined_prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true&model=flux"

            logger.debug(f"{image_url}")

            # 返回图片URL，LLM会将其整合到回复中
            return image_url

        except Exception as e:
            logger.error(f"图片生成过程中发生错误: {e}")
            raise Exception(f"生成图片时遇到问题: {str(e)}")

    @filter.command("ai生图")
    async def generate_image(self, event: AstrMessageEvent, prompt_text: str):
        """
        根据用户输入的主题，调用LLM生成英文提示词，并使用Pollinations AI生成图片。
        使用方法: /ai生图 [你的主题]
        """
        if not prompt_text:
            yield event.plain_result("请输入图片的主题，例如：/ai生图 一只猫在太空漫步")
            return

        try:
            yield event.plain_result("正在为您请求图片中，请稍候...")

            # 调用独立的 LLM 提示词生成函数
            refined_prompt = await self.generate_prompt_via_llm(prompt_text)

            encoded_prompt = urllib.parse.quote(refined_prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true&model=flux"

            logger.debug(f"生成的图片URL: {image_url}")

            yield event.image_result(image_url)

        except Exception as e:
            logger.error(f"图片生成过程中发生严重错误: {e}")
            yield event.plain_result("生成图片时遇到问题")

    async def terminate(self):
        """
        插件卸载或停用时调用的清理函数。
        """
        logger.info("花粉AI图片生成插件已卸载。")
