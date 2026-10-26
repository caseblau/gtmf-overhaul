"""fast square dilation / erosion of boolean masks (separable max filter; PIL's MaxFilter is O(k^2) per pixel)"""
import numpy as np
from scipy import ndimage as ndi

def dilate(mask, k):
    """True within a (k x k) square window of any True pixel (k odd, as PIL MaxFilter(k))"""
    return ndi.maximum_filter(mask.astype(np.uint8), size=k, mode='constant', cval=0) > 0

def erode(mask, k):
    return ndi.minimum_filter(mask.astype(np.uint8), size=k, mode='constant', cval=1) > 0

def maxf(a, k):
    """grey-level square maximum filter"""
    return ndi.maximum_filter(a, size=k, mode='nearest')
