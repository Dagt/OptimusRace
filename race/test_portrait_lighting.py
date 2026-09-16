from django.test import SimpleTestCase
from PIL import Image
import numpy as np
from .portrait import balance_portrait_light,clean_matte_edges


class PortraitLightingTests(SimpleTestCase):
    def test_light_background_spill_removed_without_changing_opaque_face(self):
        rgb=np.full((80,80,3),255,dtype=np.uint8);rgb[:,40:]=[150,100,70]
        mask=np.full((80,80),128,dtype=np.uint8);mask[:,40:]=255
        cleaned,alpha=clean_matte_edges(Image.fromarray(rgb),Image.fromarray(mask))
        self.assertLess(max(cleaned.getpixel((39,40))),230)
        self.assertLess(alpha.getpixel((39,40)),128)
        self.assertEqual(cleaned.getpixel((60,40)),(150,100,70))
    def test_dark_subject_lifted_and_bright_subject_softened(self):
        mask=Image.new('L',(100,120),255)
        for value,direction in [(50,1),(235,-1)]:
            result=balance_portrait_light(Image.new('RGB',mask.size,(value,)*3),mask)
            self.assertGreater((result.getpixel((50,50))[0]-value)*direction,0)

    def test_background_does_not_set_exposure_and_channel_ratios_preserved(self):
        mask=np.zeros((120,100),dtype=np.uint8);mask[:,25:75]=255
        alpha=Image.fromarray(mask)
        results=[]
        for background in [0,255]:
            pixels=np.full((120,100,3),background,dtype=np.uint8)
            pixels[:,25:75]=[160,120,100]
            results.append(np.asarray(balance_portrait_light(Image.fromarray(pixels),alpha))[60,50])
        np.testing.assert_array_equal(results[0],results[1])
        self.assertAlmostEqual(results[0][0]/results[0][1],160/120,delta=.02)

    def test_empty_mask_and_black_image_are_safe(self):
        image=Image.new('RGB',(100,120),'black')
        for value in [0,255]:
            result=balance_portrait_light(image,Image.new('L',image.size,value))
            self.assertEqual(result.getpixel((50,50)),(0,0,0))
